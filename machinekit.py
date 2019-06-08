import FreeCAD
import FreeCADGui
import MKServiceCommand
import MKServiceError
import MKServiceStatus
import PySide.QtCore
import PySide.QtGui
import machinetalk.protobuf.message_pb2 as MESSAGE
import machinetalk.protobuf.types_pb2 as TYPES
import os
import threading
import zeroconf
import zmq

MKServiceRegister = {
        'command' : MKServiceCommand.MKServiceCommand,
        'error'   : MKServiceError.MKServiceError,
        'status'  : MKServiceStatus.MKServiceStatus,
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

    def addService(self, properties, name):
        service = properties[b'service']
        with self.lock:
            self.endpoint[service.decode()] = Endpoint(service, name, properties)
            self.quit = False
            if self.thread is None:
                self.thread = threading.Thread(target=self.run)
                self.thread.start()

    def removeService(self, name):
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

    def __str__(self):
        with self.lock:
            return "MK(%s): %s" % (self.uuid.decode(), sorted([ep.service.decode() for epn, ep in self.endpoint.items()]))

    def connectServices(self, services):
        mkServices = []
        for s in services:
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
                            mkServices.append(service)
                else:
                    mkServices.append(self.service[s])
        return mkServices

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
                                if rx.type == TYPES.MT_PING:
                                    service.ping()
                                else:
                                    service.process(rx);
                        else:
                            #print('-', name)
                            pass

        print('thread stop')

class ServiceMonitor(object):
    def __init__(self):
        self.zc = zeroconf.Zeroconf()
        self.quit = False
        self.browser = zeroconf.ServiceBrowser(self.zc, "_machinekit._tcp.local.", self)
        self.machinekit = {}

    # zeroconf.ServiceBrowser interface
    def remove_service(self, zc, typ, name):
        for mkn, mk in self.machinekit.items():
            mk.removeService(name)

    def add_service(self, zc, typ, name):
        info = zc.get_service_info(typ, name)
        if info.properties.get(b'service'):
            uuid = info.properties[b'uuid']
            mk = self.machinekit.get(uuid)
            if not mk:
                mk = Machinekit(uuid, info.properties)
                self.machinekit[uuid] = mk
            mk.addService(info.properties, info.name)
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

def Instances(services):
    return _ServiceMonitor.instances(services)

def PathSource():
    return os.path.dirname(__file__)

def FileResource(filename):
    return "%s/Resources/%s" % (PathSource(), filename)

def IconResource(filename):
    return PySide.QtGui.QIcon(FileResource(filename))

jog = None

class Jog(object):
    def __init__(self, mk):
        global jog
        jog = self
        self.mk = mk
        self.ui = FreeCADGui.PySideUic.loadUi(FileResource('jog.ui'))

        self.services = self.mk.connectServices(['command', 'status'])
        for service in self.services:
            if 'command' == service.name:
                self.cmd = service
            service.attach(self)

        def setupJogButton(b, axes, icon):
            b.clicked.connect(lambda : self.jogAxes(axes))
            b.setIcon(IconResource(icon))
            b.setText('')

        def setupSetButton(b, axes, value, width):
            b.setMaximumWidth(width)
            b.clicked.connect(lambda : self.setAxes(axes, value))

        setupJogButton(self.ui.jogN,  'Y',  'arrow-up.svg')
        setupJogButton(self.ui.jogNE, 'xY', 'arrow-right-up.svg')
        setupJogButton(self.ui.jogE,  'x',  'arrow-right.svg')
        setupJogButton(self.ui.jogSE, 'xy', 'arrow-right-down.svg')
        setupJogButton(self.ui.jogS,  'y',  'arrow-down.svg')
        setupJogButton(self.ui.jogSW, 'Xy', 'arrow-left-down.svg')
        setupJogButton(self.ui.jogW,  'X',  'arrow-left.svg')
        setupJogButton(self.ui.jogNW, 'XY', 'arrow-left-up.svg')
        setupJogButton(self.ui.jog0,  '+',  'home-xy.svg')

        setupJogButton(self.ui.jogU,  'Z',  'arrow-up.svg')
        setupJogButton(self.ui.jogD,  'z',  'arrow-down.svg')
        setupJogButton(self.ui.jogZ0, '-',  'home-z.svg')

        buttonWidth = self.ui.setX.size().height()
        setupSetButton(self.ui.setX,      'x', self.ui.posX.value(), buttonWidth)
        setupSetButton(self.ui.setY,      'y', self.ui.posY.value(), buttonWidth)
        setupSetButton(self.ui.setZ,      'z', self.ui.posZ.value(), buttonWidth)
        setupSetButton(self.ui.setX0,     'x',                    0, buttonWidth)
        setupSetButton(self.ui.setY0,     'y',                    0, buttonWidth)
        setupSetButton(self.ui.setZ0,     'z',                    0, buttonWidth)
        setupSetButton(self.ui.setXYZ0, 'xyz',                    0, buttonWidth)

    def terminate(self):
        pass

    def jogAxes(self, axes):
        print('jog:', axes)

    def setAxes(self, axes):
        print('set', axes)

    def isConnected(self, topics=None):
        if topics is None:
            topics = ['status.config', 'status.io', 'status.motion']

        for topic in topics:
            service = self[topic]
            if service is None or not service.isValid():
                return False
        return not self.cmd is None

    def __getitem__(self, index):
        path = index.split('.')
        for service in self.services:
            if service.name == path[0]:
                if len(path) > 1:
                    return service[path[1:]]
                return service
        return None

    def updateUI(self):
        if self.isConnected():
            self.ui.setWindowTitle(self['status.config.name'])

    def changed(self, service, msg):
        if service.topicName() == 'status.config':
            self.updateUI()

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
