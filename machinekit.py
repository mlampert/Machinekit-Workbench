import FreeCAD
import FreeCADGui
import MachinekitInstance
import PathScripts.PathLog as PathLog
import PySide.QtCore
import PySide.QtGui
import itertools
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

PathLog.setLevel(PathLog.Level.NOTICE, PathLog.thisModule())
PathLog.trackModule(PathLog.thisModule())

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

    def disconnect(self):
        super().disconnect(self)

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
                PathLog.debug("TC clear")
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
                    PathLog.debug("TC confirm")
                    service.toolChanged(self.command, True)
                else:
                    PathLog.debug("TC abort")
                    self.mk.connectWith('command').sendCommand(MKCommandTaskAbort())
        elif msg.toolChanged():
            PathLog.debug('TC reset')
            service.toolChanged(self.command, False)
        else:
            PathLog.debug('TC -')
            pass

    def getTC(self, nr):
        job = self.mk.getJob()
        if job:
            for tc in job.ToolController:
                if tc.ToolNumber == nr:
                    return tc
        return None

class Machinekit(PySide.QtCore.QObject):
    statusUpdate    = PySide.QtCore.Signal(object, object)
    errorUpdate     = PySide.QtCore.Signal(object, object)
    commandUpdate   = PySide.QtCore.Signal(object, object)
    halUpdate       = PySide.QtCore.Signal(object, object)

    Context = zmq.Context()
    Poller  = zmq.Poller()

    def __init__(self, instance):
        super().__init__() # for qt signals

        self.instance = instance
        self.nam = None
        self.lock = threading.Lock()

        self.service = {}
        self.manualToolChangeNotifier = _ManualToolChangeNotifier(self)
        self.job = None

        for service in _MKServiceRegister:
            if service:
                self.service[service] = None

    def __str__(self):
        with self.lock:
            return "%s(%s): %s" % (self.name(), self.instance.uuid.decode(), sorted(self.instance.services()))

    def __getitem__(self, index):
        path = index.split('.')
        service = self.service.get(path[0])
        if service:
            if len(path) > 1:
                return service[path[1:]]
            return service
        return None

    def _update(self):
        def removeService(s, service):
            if s and service:
                self.Poller.unregister(service.socket)
                self.service[s] = None
                service.detach(self)
            return None

        with self.lock:
            # first check if all services are still available
            poll = False
            for s in self.service:
                ep = self.instance.endpointFor(s)
                service = self.service.get(s)
                if ep is None:
                    if not service is None:
                        PathLog.debug("Removing stale service: %s.%s" % (self.name(), s))
                        service = removeService(s, service)
                else:
                    if service and ep.dsn != service.dsn:
                        PathLog.debug("Removing stale service: %s.%s" % (self.name(), s))
                        service = removeService(s, service)
                    if service is None:
                        cls = _MKServiceRegister.get(s)
                        if cls is None:
                            PathLog.error("service %s not supported" % s)
                        else:
                            PathLog.info("Connecting to service: %s.%s" % (self.name(), s))
                            service = cls(self.Context, s, ep.properties)
                            self.service[s] = service
                            service.attach(self)
                            self.Poller.register(service.socket, zmq.POLLIN)
                            poll = True
                    else:
                        poll = True

            # if there is at least one service connected check if there are any messages to process
            while poll:
                # As it turns out the poller only ever returns a single pair so we want to call it
                # in a loop to get all pending updates. However, they might fix the behaviour according
                # to the docs and I don't want that to break this client. So we do both, call it in a
                # loop and pretend it could return a list of tuples.
                poll = dict(self.Poller.poll(0))
                for socket in poll:
                    for name, service in self.service.items():
                        if service.socket == socket:
                            msg = None
                            rsp = None
                            rx = MESSAGE.Container()
                            try:
                                msg = service.receiveMessage()
                                rx.ParseFromString(msg)
                            except Exception as e:
                                PathLog.error("%s exception: %s" % (service.name, e))
                                PathLog.error("    msg = '%s'" % msg)
                            else:
                                # ignore all ping messages for now
                                if rx.type != TYPES.MT_PING:
                                    #PathLog.debug(rx)
                                    service.process(rx);
                            break

            for name, service in self.service.items():
                if service:
                    service.ping()

    def changed(self, service, msg):
        PathLog.track(service)
        if 'status.' in service.topicName():
            self.statusUpdate.emit(self, msg)
        elif 'hal' in service.topicName():
            self.halUpdate.emit(self, msg)
        elif 'error' in service.topicName():
            self.errorUpdate.emit(self, msg)
            display = PathLog.info
            if msg.isError():
                display = PathLog.error
            if msg.isText():
                display = PathLog.notice
            for m in msg.messages():
                display(m)
        elif 'command' in service.topicName():
            self.commandUpdate.emit(self, msg)

    def providesServices(self, services):
        if services is None:
            services = self.service
        return all([not self.service[s] is None for s in services])

    def isValid(self):
        if self['status'] is None:
            return False
        if not self['status'].isValid():
            return False
        if self['command'] is None:
            return False
        return True

    def isPowered(self):
        return self.isValid() and (not self['status.io.estop']) and self['status.motion.enabled']

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

    def name(self):
        if self.nam is None:
            self.nam = self['status.config.name']
            if self.nam is None:
                return self.instance.uuid
        return self.nam

_Services = MachinekitInstance.ServiceMonitor()

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
    pass

def Instances(services=None):
    '''Instances(services=None) ... Answer a list of all discovered Machinekit instances which provide all services listed.
    If no services are requested all discovered MK instances are returned.'''
    return _Services.instances(services)

_active = None

def Activate(mk):
    '''Activate(mk) ... makes the given machinekit instance the currently active one.
All communication and commands are for the activated MK instance. If there is only one
MK instance it is automatically used as the active MK instance.'''
    global _active
    PathLog.track(mk)
    _active = mk
    if hud:
        hud.updateUI()
    if jog:
        jog.updateUI()
    if execute:
        execute.updateUI()


def update():
    for mk in [inst for inst in Instances() if inst.isValid()]:
        mtc = mk.manualToolChangeNotifier
        if not mtc.isConnected():
            mtc.connect()
        if not mk.error and mk['error']:
            mk.error = ServiceConnector(mk.connectWith('error'), mk)

def Active():
    '''Active() ... return the currently active MK instance.
If there is only instance it is automatically used as the active one.'''
    global _active
    if _active and not _active.isValid():
        _active = None
        if hud:
            hud.updateUI()
        if jog:
            jog.updateUI()
        if execute:
            execute.updateUI()

    return _active

def Any():
    '''Any() ... returns a Machinekit instance, if at least one was discovered.'''
    mks = [inst for inst in _Services.instances(None) if inst.isValid()]
    if mks:
        return mks[0]
    return None

def Power(mk):
    '''Power() ... unlocks estop and toggles power of the given MK'''
    if not mk:
        mk = Active()
    if mk:
        status = mk.connectWith('status')
        command = mk.connectWith('command')

        commands = []
        if status['io.estop']:
            commands.append(MKCommandEstop(False))
        commands.append(MKCommandPower(not mk.isPowered()))
        command.sendCommands(commands)

def Home(mk):
    '''Home(mk) ... homes all axis of the given MK'''
    if not mk:
        mk = Active()
    if mk:
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

def MDI(cmd):
    '''MID(cmd, mk=None) ... executes cmd on the active MK'''
    mk = Active()
    if mk:
        mk.mdi(cmd)

def New():
    return Machinekit(_Services.instances(None)[0])

# these are for debugging and development - do not use
hud     = None
jog     = None
execute = None

