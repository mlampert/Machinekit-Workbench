import FreeCAD
import FreeCADGui
import PySide.QtCore
import PySide.QtGui
import machinekit
import machinetalk.protobuf.status_pb2 as STATUS

class TreeSelectionObserver(object):
    def __init__(self, notify):
        self.notify = notify

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
        self.ui = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('execute.ui'), self)

        self.connectors = []
        self.services = self.mk.connectServices(['command', 'status'])
        for service in self.services:
            if 'command' == service.name:
                self.cmd = service
            self.connectors.append(machinekit.ServiceConnector(service, self))

        self.oi = 'v'
        if True:
            lo = PySide.QtGui.QHBoxLayout()
            lo.setSpacing(0)
            lo.setContentsMargins(0, 0, 0, 0)

            tb = PySide.QtGui.QFrame()
            tb.setFrameShape(PySide.QtGui.QFrame.Box)
            tb.setLayout(lo)
            #tb.setContentsMargins(0, 0, 0, 0)

            self.title = PySide.QtGui.QLabel()
            self.title.setText('-.-')
            self.title.setContentsMargins(0, 0, 0, 0)
            lo.addWidget(self.title, 10)

            self.ob = PySide.QtGui.QPushButton()
            #self.ob.setFlat(False)
            self.ob.setIcon(PySide.QtGui.QApplication.style().standardIcon(PySide.QtGui.QStyle.SP_TitleBarUnshadeButton))
            self.ob.clicked.connect(self.toggleOrientation)
            lo.addWidget(self.ob)

            bs = None
            for b in self.ui.findChildren(PySide.QtGui.QAbstractButton):
                if 'qt_dockwidget' in b.objectName():
                    bt = PySide.QtGui.QPushButton()
                    bt.setIcon(b.icon())
                    bs = b.size()
                    if bs.height() < bs.width():
                        bs.setWidth(bs.height())
                    else:
                        bs.setHeight(bs.width())
                    bt.setMaximumSize(bs)
                    #bt.setFlat(False)
                    bt.setContentsMargins(0, 0, 0, 0)
                    bt.clicked.connect(b.click)
                    lo.addWidget(bt)
            if bs:
                self.title.setMaximumHeight(bs.height())
                self.ob.setMaximumSize(bs)
                #tb.setMaximumHeight(bs.height())
                print(bs)

            self.ui.setTitleBarWidget(tb)

        self.job = None

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

        self.updateUI()
        machinekit.execute = self

    def __getitem__(self, index):
        path = index.split('.')
        for service in self.services:
            if service.name == path[0]:
                if len(path) > 1:
                    return service[path[1:]]
                return service
        return None

    def terminate(self):
        FreeCADGui.Selection.removeObserver(self.observer)

    def isConnected(self, topics=None):
        if topics is None:
            topics = ['status.config', 'status.io', 'status.motion']

        for topic in topics:
            service = self[topic]
            if service is None or not service.isValid():
                return False
        return not self.cmd is None

    def objectSelectionChanged(self):
        jobs = [sel.Object for sel in FreeCADGui.Selection.getSelectionEx() if sel.Object.Name.startswith('Job')]
        if len(jobs) == 1:
            self.job = jobs[0]
        else:
            self.job = None

        self.ui.load.setEnabled(self.isIdle() and not self.job is None)

    def toggleOrientation(self):
        if 'v' == self.oi:
            self.ui.execute.layout().setDirection(PySide.QtGui.QBoxLayout.TopToBottom)
            self.ob.setIcon(PySide.QtGui.QApplication.style().standardIcon(PySide.QtGui.QStyle.SP_TitleBarShadeButton))
            self.oi = 'h'
        else:
            self.ui.execute.layout().setDirection(PySide.QtGui.QBoxLayout.LeftToRight)
            self.ob.setIcon(PySide.QtGui.QApplication.style().standardIcon(PySide.QtGui.QStyle.SP_TitleBarUnshadeButton))
            self.oi = 'v'

    def isState(self, state):
        return STATUS.EmcInterpStateType.Value(state) == self['status.interp.state']

    def isIdle(self):
        return self.isState('EMC_TASK_INTERP_IDLE')
    def isPaused(self):
        return self.isState('EMC_TASK_INTERP_PAUSED')

    def updateExecute(self, connected, powered):
        if connected and powered:
            if self.isIdle():
                self.ui.load.setEnabled(not self.job is None)
                self.ui.run.setEnabled(self['status.task.file'] != '')
                self.ui.step.setEnabled(self['status.task.file'] != '')
                self.ui.pause.setEnabled(False)
                self.ui.stop.setEnabled(False)
            else:
                self.ui.load.setEnabled(False)
                self.ui.run.setEnabled(False)
                self.ui.step.setEnabled(self.isPaused())
                self.ui.pause.setEnabled(True)
                if self.ui.pause.isChecked() != self.isPaused():
                    self.ui.pause.setChecked(self.isPaused())
                self.ui.stop.setEnabled(True)

            mode = STATUS.EmcTaskModeType.Name(self['status.task.task.mode']).split('_')[3].lower()
            state = ' '.join(STATUS.EmcTaskExecStateType.Name(self['status.task.state']).split('_')[3:]).lower()
            if mode == 'auto':
                istate = STATUS.EmcInterpStateType.Name(self['status.interp.state']).split('_')[3].lower()
                mode = "%s.%s" % (mode, istate)
            self.ui.status.setText("%s:%s (%d/%d)" % (mode, state, self['status.motion.line'], self['status.task.line.total']))

    def updateUI(self):
        connected = self.isConnected()
        powered = self.mk.isPowered()

        self.updateExecute(connected, powered)
        self.ui.dockWidgetContents.setEnabled(powered)

    def changed(self, service, updated):
        self.updateUI()
