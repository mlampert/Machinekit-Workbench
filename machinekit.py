import FreeCAD
import FreeCADGui
import PySide.QtCore
import PySide.QtGui
import machinetalk.protobuf.message_pb2 as MESSAGE
import machinetalk.protobuf.status_pb2 as STATUS
import machinetalk.protobuf.types_pb2 as TYPES
import os
import threading
import zeroconf
import zmq

from MKServiceCommand import *
from MKServiceError import *
from MKServiceStatus import *
from MKServiceHal import *

AxesForward  = ['X', 'Y', 'Z', 'A', 'B', 'C', 'U', 'V', 'W']
AxesBackward = ['x', 'y', 'z', 'a', 'b', 'c', 'u', 'v', 'w']
AxesName     = AxesForward


MKServiceRegister = {
        'command'   : MKServiceCommand,
        'error'     : MKServiceError,
        'halrcmd'   : MKServiceHalCommand,
        'halrcomp'  : MKServiceHalStatus,
        'status'    : MKServiceStatus,
        '': None
        }

class ServiceConnector(PySide.QtCore.QObject):
    updated = PySide.QtCore.Signal(object, object)

    def __init__(self, service, observer):
        super().__init__()
        self.service = service
        self.observer = observer

        self.updated.connect(observer.changed)
        self.service.attach(self)

    def changed(self, service, arg):
        self.updated.emit(service, arg)

    def disconnect(self):
        self.updated.disconnect()

class Endpoint(object):
    def __init__(self, service, name, addr, prt, properties):
        self.service = service
        self.name = name
        self.addr = addr
        self.prt = prt
        self.properties = properties
        self.dsn = properties[b'dsn']
        self.uuid = properties[b'instance']
        print("machinetalk.%-13s %s:%d" % (self.service.decode(), self.address(), self.port()))

    def addressRaw(self):
        return self.addr
    def address(self):
        return "%d.%d.%d.%d" % (self.addr[0], self.addr[1], self.addr[2], self.addr[3])
    def port(self):
        return self.prt

class ManualToolChangeNotifier(object):
    def __init__(self, mk):
        self.mk = mk
        self.status = None
        self.command = None
        self.connectors = []
        self.connect()

    def disconnect(self):
        for connector in self.connectors:
            connector.disconnect()
        self.connectors = []
        self.status = None
        self.command = None

    def connect(self):
        if self.status:
            self.disconnect()
        if self.command:
            self.disconnect()
        self.status = self.mk.connectWith('halrcomp')
        self.command = self.mk.connectWith('halrcmd')
        if self.status and self.command:
            self.connectors.append(ServiceConnector(self.status, self))
            self.connectors.append(ServiceConnector(self.command, self))
        else:
            self.status = None
            self.command = None

    def changed(self, service, tc):
        if tc.changeTool():
            if 0 == tc.toolNumber():
                print("TC clear")
                service.toolChanged(self.command, True)
            else:
                mb = PySide.QtGui.QMessageBox()
                mb.setWindowIcon(IconResource('machinekiticon.png'))
                mb.setWindowTitle('Machinekit')
                mb.setText( "Insert tool #%d and then press OK." % tc.toolNumber())
                mb.setIcon(PySide.QtGui.QMessageBox.Warning)
                mb.setStandardButtons(PySide.QtGui.QMessageBox.Ok | PySide.QtGui.QMessageBox.Abort)
                if PySide.QtGui.QMessageBox.Ok == mb.exec_():
                    print("TC confirm")
                    service.toolChanged(self.command, True)
                else:
                    print("TC abort")
                    self.mk.connectWith('command').sendCommand(MKCommandTaskAbort())
        elif tc.toolChanged():
            print('TC reset')
            service.toolChanged(self.command, False)
        else:
            print('TC -')

class Machinekit(PySide.QtCore.QThread):
    def __init__(self, uuid, properties):
        super(self.__class__, self).__init__()

        self.uuid = uuid
        self.properties = properties
        self.endpoint = {}
        self.lock = threading.Lock()
        self.service = {}
        # setup zmq
        self.context = zmq.Context()
        self.poller = zmq.Poller()
        self.quit = False
        self.timeout = 100
        self.thread = None
        self.manualToolChangeNotifier = None

    def __str__(self):
        with self.lock:
            return "MK(%s): %s" % (self.uuid.decode(), sorted([ep.service.decode() for epn, ep in self.endpoint.items()]))

    def __getitem__(self, index):
        path = index.split('.')
        service = self.service.get(path[0])
        if service:
            if len(path) > 1:
                return service[path[1:]]
            return service
        return None

    def _addService(self, properties, name, address, port):
        service = properties[b'service']
        with self.lock:
            self.endpoint[service.decode()] = Endpoint(service, name, address, port, properties)
            self.quit = False
            if self.thread is None:
                self.thread = self
                self.thread.start()
        if service == b'status':
            s = self.connectWith(service.decode())
        if service in [b'halrcmd', b'halrcomp'] and self.manualToolChangeNotifier:
            self.manualToolChangeNotifier.connect()

    def startManualToolChangeNotifier(self):
        if self.manualToolChangeNotifier is None:
            self.manualToolChangeNotifier = ManualToolChangeNotifier(self)

    def _removeService(self, name):
        with self.lock:
            for epn, ep in self.endpoint.items():
                if ep.name == name:
                    if epn in [b'halrcmd', 'halrcomp'] and self.manualToolChangeNotifier:
                        self.manualToolChangeNotifier.disconnect()
                    del self.endpoint[epn]
                    break
            if 0 == len(self.endpoint):
                self.quit = True
        if not self.thread is None:
            self.thread.join
            self.thread = None

    def providesServices(self, services):
        candidates = [s for s in [self.endpoint.get(v) for v in services]]
        return all([self.endpoint.get(s) for s in services])

    def connectWith(self, s):
        with self.lock:
            if not self.service.get(s):
                cls = MKServiceRegister.get(s)
                if cls is None:
                    print("Error: service %s not supported" % s)
                else:
                    mk = self.endpoint.get(s)
                    if mk is None:
                        print("Error: no endpoint for %s" % s)
                    else:
                        service = cls(self.context, s, mk.properties)
                        self.service[s] = service
                        self.poller.register(service.socket, zmq.POLLIN)
                        return service
                return None
            return self.service[s]

    def connectServices(self, services):
        return [self.connectWith(s) for s in services]

    def run(self):
        print('thread start')
        while not self.quit:
            s = dict(self.poller.poll(self.timeout))
            if s:
                with self.lock:
                    for name, service in self.service.items():
                        if service.socket in s:
                            #print('+', name)
                            msg = None
                            rsp = None
                            rx = MESSAGE.Container()
                            try:
                                msg = service.receiveMessage()
                                rx.ParseFromString(msg)
                            except Exception as e:
                                print("%s exception: %s" % (service.name, e))
                                print("    msg = '%s'" % msg)
                            else:
                                # ignore all ping messages for now
                                if rx.type != TYPES.MT_PING:
                                    service.process(rx);
                        else:
                            #print('-', name)
                            pass
            with self.lock:
                for name, service in self.service.items():
                    service.ping()

        print('thread stop')

    def isPowered(self):
        return (not self['status.io.estop']) and self['status.motion.enabled']

    def isHomed(self):
        return self.isPowered() and all([axis.homed for axis in self['status.motion.axis']])

class ServiceMonitor(object):
    def __init__(self):
        self.zc = zeroconf.Zeroconf()
        self.quit = False
        self.browser = zeroconf.ServiceBrowser(self.zc, "_machinekit._tcp.local.", self)
        self.machinekit = {}

    # zeroconf.ServiceBrowser interface
    def remove_service(self, zc, typ, name):
        for mkn, mk in self.machinekit.items():
            mk._removeService(name)

    def add_service(self, zc, typ, name):
        info = zc.get_service_info(typ, name)
        if info and info.properties.get(b'service'):
            #print(info)
            uuid = info.properties[b'uuid']
            mk = self.machinekit.get(uuid)
            if not mk:
                mk = Machinekit(uuid, info.properties)
                self.machinekit[uuid] = mk
            mk._addService(info.properties, info.name, info.address, info.port)
            #print(mk)

    def run(self):
        while not self.quit:
            time.sleep(0.1)
        self.browser.done = True

    def printAll(self):
        for mkn, mk in self.machinekit.items():
            print(mk)

    def instances(self, services):
        return [mk for mkn, mk in self.machinekit.items() if mk.providesServices(services)]

_ServiceMonitor = ServiceMonitor()

def Instances(services = None):
    if services is None:
        return _ServiceMonitor.instances([])
    return _ServiceMonitor.instances(services)

def PathSource():
    return os.path.dirname(__file__)

def FileResource(filename):
    return "%s/Resources/%s" % (PathSource(), filename)

def IconResource(filename):
    return PySide.QtGui.QIcon(FileResource(filename))

def taskMode(service, mode, force):
    m = service['task.task.mode']
    if m is None:
        m = service['status.task.task.mode'] 
    if m != mode or force:
        return [MKCommandTaskSetMode(mode)]
    return []

def taskModeAuto(service, force=False):
    return taskMode(service, STATUS.EmcTaskModeType.Value('EMC_TASK_MODE_AUTO'), force)

def taskModeMDI(service, force=False):
    return taskMode(service, STATUS.EmcTaskModeType.Value('EMC_TASK_MODE_MDI'), force)

def taskModeManual(service, force=False):
    return taskMode(service, STATUS.EmcTaskModeType.Value('EMC_TASK_MODE_MANUAL'), force)

def Estop(mk):
    status = mk.connectWith('status')
    command = mk.connectWith('command')

    commands = []
    if status['io.estop']:
        commands.append(MKCommandEstop(False))
    commands.append(MKCommandPower(not mk.isPowered()))
    command.sendCommands(commands)

def Home(mk):
    status = mk.connectWith('status')
    command = mk.connectWith('command')

    sequence = [[cmd] for cmd in taskModeManual(status)]
    toHome = [axis.index for axis in status['motion.axis'] if not axis.homed]
    order  = {}

    for axis in status['config.axis']:
        if axis.index in toHome:
            batch = order.get(axis.home_sequence)
            if batch is None:
                batch = []
            batch.append(axis.index)
            order[axis.home_sequence] = batch

    for key in sorted(order):
        batch = order[key]
        sequence.append([MKCommandAxisHome(index, True) for index in batch])
        for index in batch:
            sequence.append([MKCommandPauseUntil(lambda index=index: status["motion.axis.%d.homed" % index])])

    command.sendCommandSequence(sequence)

hud     = None
jog     = None
execute = None

