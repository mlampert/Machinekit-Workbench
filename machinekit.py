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

AxesForward  = ['X', 'Y', 'Z', 'A', 'B', 'C', 'U', 'V', 'W']
AxesBackward = ['x', 'y', 'z', 'a', 'b', 'c', 'u', 'v', 'w']
AxesName     = AxesForward


MKServiceRegister = {
        'command' : MKServiceCommand,
        'error'   : MKServiceError,
        'status'  : MKServiceStatus,
        '': None
        }

class Endpoint(object):
    def __init__(self, service, name, properties):
        self.service = service
        self.name = name
        self.properties = properties
        self.dsn = properties[b'dsn']
        self.uuid = properties[b'instance']

class Machinekit(object):
    def __init__(self, uuid, properties):
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

    def _addService(self, properties, name):
        service = properties[b'service']
        with self.lock:
            self.endpoint[service.decode()] = Endpoint(service, name, properties)
            self.quit = False
            if self.thread is None:
                self.thread = threading.Thread(target=self._run)
                self.thread.start()
        if b'status' == service:
            self.connectServices(['status'])

    def _removeService(self, name):
        with self.lock:
            for epn, ep in self.endpoint.items():
                if ep.name == name:
                    del self.endpoint[epn]
                    break
            if 0 == len(self.endpoint):
                self.quit = True
        if not self.thread is None:
            self.thread.join

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

    def _run(self):
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
        if info.properties.get(b'service'):
            uuid = info.properties[b'uuid']
            mk = self.machinekit.get(uuid)
            if not mk:
                mk = Machinekit(uuid, info.properties)
                self.machinekit[uuid] = mk
            mk._addService(info.properties, info.name)
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

def taskMode(service, mode):
    m = service['task.task.mode']
    if m is None:
        m = service['status.task.task.mode'] 
    if m != mode:
        return [MKCommandTaskSetMode(mode)]
    return []

def taskModeAuto(service):
    return taskMode(service, STATUS.EmcTaskModeType.Value('EMC_TASK_MODE_AUTO'))

def taskModeMDI(service):
    return taskMode(service, STATUS.EmcTaskModeType.Value('EMC_TASK_MODE_MDI'))

def taskModeManual(service):
    return taskMode(service, STATUS.EmcTaskModeType.Value('EMC_TASK_MODE_MANUAL'))

jog = None

class TreeSelectionObserver(object):
    def __init__(self, notify):
        self.notify = notify
        self.job = None

    def addSelection(self, doc, obj, sub, pnt):
        self.notify()

    def removeSelection(self, doc, obj, sub):
        self.notify()

    def setSelection(self, doc, something=None):
        self.notify()

    def clearSelection(self, doc):
        self.notify()

class EventFilter(PySide.QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == PySide.QtCore.QChildEvent.Resize:
            print(event.type(), event.size())
        return PySide.QtCore.QObject.eventFilter(self, obj, event)

class Execute(object):
    def __init__(self, mk):
        self.mk = mk
        self.ui = FreeCADGui.PySideUic.loadUi(FileResource('execute.ui'), self)
        if True:
            tb = PySide.QtGui.QWidget()
            lo = PySide.QtGui.QHBoxLayout()
            tb.setLayout(lo)
            tb.setContentsMargins(0, 0, 0, 0)
            self.title = PySide.QtGui.QLabel()
            self.title.setText('hugo')
            self.title.setContentsMargins(0, 0, 0, 0)
            lo.addWidget(self.title)
            spacer = PySide.QtGui.QSpacerItem(0,0,PySide.QtGui.QSizePolicy.Expanding, PySide.QtGui.QSizePolicy.Minimum)
            lo.addItem(spacer)
            self.ob = PySide.QtGui.QPushButton()
            self.ob.setFlat(True)
            self.ob.setIcon(PySide.QtGui.QApplication.style().standardIcon(PySide.QtGui.QStyle.SP_ToolBarVerticalExtensionButton))
            self.ob.clicked.connect(self.toggleOrientation)
            self.oi = 'v'
            bs = None
            lo.addWidget(self.ob)
            for b in self.ui.findChildren(PySide.QtGui.QAbstractButton):
                if 'qt_dockwidget' in b.objectName():
                    bt = PySide.QtGui.QPushButton()
                    bt.setIcon(b.icon())
                    print(b.icon().name())
                    bs = b.icon().availableSizes()[-1] + PySide.QtCore.QSize(3,3)
                    bt.setMaximumSize(bs)
                    bt.setFlat(True)
                    bt.clicked.connect(b.click)
                    lo.addWidget(bt)
            if bs:
                self.ob.setMaximumSize(bs)
            lo.setSpacing(0)
            lo.setContentsMargins(0, 0, 0, 0)
            self.ui.setTitleBarWidget(tb)
        self.job = None

        #self.ui.dockWidgetContents.resized.connect(self.resized)

        self.ui.run.clicked.connect(lambda : self.ui.status.setText('run'))
        self.ui.step.clicked.connect(lambda : self.ui.status.setText('step'))
        self.ui.pause.clicked.connect(lambda p: self.ui.status.setText("pause: %s" % p))
        self.ui.stop.clicked.connect(lambda : self.ui.status.setText('stop'))
        self.ui.run.clicked.connect(lambda : _ServiceMonitor.printAll())

        self.ui.status.setText('')
        rect = self.ui.geometry()
        self.ui.resize(rect.width(), 0)

        self.observer = TreeSelectionObserver(self.objectSelectionChanged)
        FreeCADGui.Selection.addObserver(self.observer)
        self.objectSelectionChanged()

        #self.eventFilter = EventFilter()
        #self.ui.installEventFilter(self.eventFilter)

    def terminate(self):
        FreeCADGui.Selection.removeObserver(self.observer)

    def resized(self):
        print('resized')

    def objectSelectionChanged(self):
        jobs = [sel.Object for sel in FreeCADGui.Selection.getSelectionEx() if sel.Object.Name.startswith('Job')]
        if len(jobs) == 1 and jobs[0] != self.job:
            self.job = jobs[0]
        else:
            self.job = None

        if self.job is None:
            self.ui.run.setEnabled(False)
            self.ui.step.setEnabled(False)
        else:
            self.ui.run.setEnabled(True)
            self.ui.step.setEnabled(True)

    def toggleOrientation(self):
        if 'v' == self.oi:
            self.ui.execute.layout().setDirection(PySide.QtGui.QBoxLayout.TopToBottom)
            self.ob.setIcon(PySide.QtGui.QApplication.style().standardIcon(PySide.QtGui.QStyle.SP_ToolBarHorizontalExtensionButton))
            self.oi = 'h'
        else:
            self.ui.execute.layout().setDirection(PySide.QtGui.QBoxLayout.LeftToRight)
            self.ob.setIcon(PySide.QtGui.QApplication.style().standardIcon(PySide.QtGui.QStyle.SP_ToolBarVerticalExtensionButton))
            self.oi = 'v'

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

