import FreeCAD
import FreeCADGui
import PathScripts.PathLog as PathLog
import PySide.QtCore
import PySide.QtGui
import machinetalk.protobuf.message_pb2 as MESSAGE
import machinetalk.protobuf.status_pb2 as STATUS
import machinetalk.protobuf.types_pb2 as TYPES
import os
import threading
import zeroconf
import zmq

from MKCommand          import *
from MKServiceCommand   import *
from MKServiceError     import *
from MKServiceStatus    import *
from MKServiceHal       import *

AxesForward  = ['X', 'Y', 'Z', 'A', 'B', 'C', 'U', 'V', 'W']
AxesBackward = ['x', 'y', 'z', 'a', 'b', 'c', 'u', 'v', 'w']
AxesName     = AxesForward


_MKServiceRegister = {
        'command'   : MKServiceCommand,
        'error'     : MKServiceError,
        'halrcmd'   : MKServiceHalCommand,
        'halrcomp'  : MKServiceHalStatus,
        'status'    : MKServiceStatus,
        '': None
        }

class ServiceConnector(PySide.QtCore.QObject):
    '''Internal class for propagating change notifications from one thread to the main thread (UI).
    It is important that instances of this class are created in the main thread, otherwise QT's
    signal mechanism does not propagate the signals properly.'''
    updated = PySide.QtCore.Signal(object, object)

    def __init__(self, service, observer):
        super().__init__()
        self.service = service
        self.observer = observer

        self.updated.connect(observer.changed)
        self.service.attach(self)

    def changed(self, service, arg):
        self.updated.emit(service, arg)

    def separate(self):
        self.updated.disconnect()

class _Endpoint(object):
    '''POD for describing a service end point.'''

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

class _ManualToolChangeNotifier(object):
    '''Class to prompt user to perform a tool change and confirm its completion.'''
    def __init__(self, mk):
        self.mk = mk
        self.status = None
        self.command = None
        self.connectors = []

    def disconnect(self):
        for connector in self.connectors:
            connector.disconnect()
        self.connectors = []
        self.status = None
        self.command = None

    def connect(self):
        if self.status or self.command:
            self.disconnect()
        if self.mk.providesServices(['halrcomp', 'halrcmd']):
            self.status = self.mk.connectWith('halrcomp')
            self.command = self.mk.connectWith('halrcmd')
            self.connectors.append(ServiceConnector(self.status, self))
            self.connectors.append(ServiceConnector(self.command, self))

    def isConnected(self):
        return self.status and self.command and self.connectors

    def changed(self, service, msg):
        if msg.changeTool():
            if 0 == msg.toolNumber():
                #print("TC clear")
                service.toolChanged(self.command, True)
            else:
                tc = self.getTC(msg.toolNumber())
                if tc:
                    msg = ["Insert tool #%d" % tc.ToolNumber, "<i>\"%s\"</i>" % tc.Label]
                else:
                    msg = ["Insert tool #%d" % msg.toolNumber()]
                mb = PySide.QtGui.QMessageBox()
                mb.setWindowIcon(IconResource('machinekiticon.png'))
                mb.setWindowTitle('Machinekit')
                mb.setTextFormat(PySide.QtCore.Qt.TextFormat.RichText)
                mb.setText("<div align='center'>%s</div>" % '<br/>'.join(msg))
                mb.setIcon(PySide.QtGui.QMessageBox.Warning)
                mb.setStandardButtons(PySide.QtGui.QMessageBox.Ok | PySide.QtGui.QMessageBox.Abort)
                if PySide.QtGui.QMessageBox.Ok == mb.exec_():
                    #print("TC confirm")
                    service.toolChanged(self.command, True)
                else:
                    #print("TC abort")
                    self.mk.connectWith('command').sendCommand(MKCommandTaskAbort())
        elif msg.toolChanged():
            #print('TC reset')
            service.toolChanged(self.command, False)
        else:
            #print('TC -')
            pass

    def getTC(self, nr):
        job = self.mk.getJob()
        if job:
            for tc in job.ToolController:
                if tc.ToolNumber == nr:
                    return tc
        return None

class _Thread(PySide.QtCore.QThread):
    '''Internal class to poll for messages from MK. DO NOT USE.'''

    def __init__(self, mk):
        super(_Thread, self).__init__()
        self.mk = mk
        self.timeout = 100

    def run(self):
        print('thread start')
        while not self.mk.quit:
            s = dict(self.mk.poller.poll(self.timeout))
            if s:
                with self.mk.lock:
                    for name, service in self.mk.service.items():
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
                                    #print(rx)
                                    service.process(rx);
                        else:
                            #print('-', name)
                            pass
            with self.mk.lock:
                for name, service in self.mk.service.items():
                    service.ping()

        print('thread stop')


class Machinekit(object):
    '''Main interface to the services of a MK instance. Tracks the dynamic registration and unregistration of services
    and prints the error messages to the log stream.'''

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
        self.thread = None
        self.manualToolChangeNotifier = _ManualToolChangeNotifier(self)
        self.job = None
        self.error = None

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
            self.endpoint[service.decode()] = _Endpoint(service, name, address, port, properties)
            self.quit = False
            if self.thread is None:
                self.thread = _Thread(self)
                self.thread.start()
        if service in [b'error', b'status']:
            s = self.connectWith(service.decode())

    def _removeService(self, name):
        with self.lock:
            if name == 'error' and self.error:
                self.error.separate()
                self.error = None

            for epn, ep in self.endpoint.items():
                if ep.name == name:
                    if epn in [b'halrcmd', 'halrcomp']:
                        self.manualToolChangeNotifier.disconnect()
                    del self.endpoint[epn]
                    break
            if 0 == len(self.endpoint):
                self.quit = True
        if self.quit and self.thread:
            self.thread.join()
            self.thread = None

    def changed(self, service, msg):
        display = PathLog.info
        if msg.isError():
            display = PathLog.error
        if msg.isText():
            display = PathLog.notice
        for m in msg.messages():
            display(m)

    def providesServices(self, services):
        candidates = [s for s in [self.endpoint.get(v) for v in services]]
        return all([self.endpoint.get(s) for s in services])

    def connectWith(self, s):
        with self.lock:
            if not self.service.get(s):
                cls = _MKServiceRegister.get(s)
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

    def isPowered(self):
        return (not self['status.io.estop']) and self['status.motion.enabled']

    def isHomed(self):
        return self.isPowered() and all([axis.homed != 0 for axis in self['status.motion.axis']])

    def setJob(self, job):
        self.job = job

    def getJob(self):
        return self.job

    def mdi(self, cmd):
        command = self.connectWith('command')
        status = self.connectWith('status')
        if status and command:
            sequence = taskModeMDI(self)
            sequence.append(MKCommandTaskExecute(cmd))
            command.sendCommands(sequence)

class _ServiceMonitor(object):
    '''Singleton for the zeroconf service discovery. DO NOT USE.'''
    _Instance = None

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
        return [mk for mkn, mk in self.machinekit.items() if services is None or mk.providesServices(services)]

    @classmethod
    def Start(cls):
        if cls._Instance is None:
            cls._Instance = _ServiceMonitor()

    @classmethod
    def Instance(cls):
        cls.Start()
        return cls._Instance

def _taskMode(service, mode, force):
    '''internal - do not use'''
    m = service['task.task.mode']
    if m is None:
        m = service['status.task.task.mode'] 
    if m != mode or force:
        return [MKCommandTaskSetMode(mode)]
    return []

def taskModeAuto(service, force=False):
    '''taskModeAuto(service, force=False) ... return a list of commands required to switch to AUTO mode.'''
    return _taskMode(service, STATUS.EmcTaskModeType.Value('EMC_TASK_MODE_AUTO'), force)

def taskModeMDI(service, force=False):
    '''taskModeMDI(service, force=False) ... return a list of commands required to switch to MDI mode.'''
    return _taskMode(service, STATUS.EmcTaskModeType.Value('EMC_TASK_MODE_MDI'), force)

def taskModeManual(service, force=False):
    '''taskModeManual(service, force=False) ... return a list of commands required to switch to MANUAL mode.'''
    return _taskMode(service, STATUS.EmcTaskModeType.Value('EMC_TASK_MODE_MANUAL'), force)

def PathSource():
    '''PathSource() ... return the path to the workbench'''
    return os.path.dirname(__file__)

def FileResource(filename):
    '''FileResource(filename) ... return the full path of the given resource file.'''
    return "%s/Resources/%s" % (PathSource(), filename)

def IconResource(filename):
    '''IconResource(filename) ... return a QtGui.QIcon from the given resource file (which must exist in the Resource directory).'''
    return PySide.QtGui.QIcon(FileResource(filename))

def Start():
    '''Start() ... internal function used to start the service discovery.'''
    _ServiceMonitor.Start()

def Instances(services=None):
    '''Instances(services=None) ... Answer a list of all discovered Machinekit instances which provide all services listed.
    If no services are requested all discovered MK instances are returned.'''
    return _ServiceMonitor.Instance().instances(services)

def Any():
    '''Any() ... returns a Machinekit instance, if at least one was discovered.'''
    # this function gets called periodically through the MachineCommands observers
    # we'll abuse it to connect manual tool changer, which has to happen in the main
    # thread - otherwise the notifications vanish into thin air
    mks = _ServiceMonitor.Instance().instances(None)
    if mks:
        for mk in mks:
            mtc = mk.manualToolChangeNotifier
            if not mtc.isConnected():
                mtc.connect()
            if not mk.error and mk['error']:
                mk.error = ServiceConnector(mk.connectWith('error'), mk)
        return mks[0]
    return None

def Estop(mk=None):
    '''Estop(mk=None) ... unlocks estop and toggles power, if no MK instance is provided Any() is used.'''
    if mk is None:
        mk = Any()
    status = mk.connectWith('status')
    command = mk.connectWith('command')

    commands = []
    if status['io.estop']:
        commands.append(MKCommandEstop(False))
    commands.append(MKCommandPower(not mk.isPowered()))
    command.sendCommands(commands)

def Home(mk=None):
    '''Home(mk=None) ... homes all axis, if no MK instance is provided Any() is used.'''
    if mk is None:
        mk = Any()
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
            sequence.append([MKCommandWaitUntil(lambda index=index: status["motion.axis.%d.homed" % index])])

    command.sendCommandSequence(sequence)

def MDI(cmd, mk=None):
    '''MID(cmd, mk=None) ... executes cmd on the provided MK instance, if no MK is provided Any() is used.'''
    if mk is None:
        mk = Any()
    mk.mdi(cmd)


# these are for debugging and development - do not use
hud     = None
jog     = None
execute = None

