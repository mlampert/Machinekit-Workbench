import FreeCAD
import FreeCADGui
import PathScripts.PathPost as PathPost
import PathScripts.PathUtil as PathUtil
import PySide.QtCore
import PySide.QtGui
import ftplib
import io
import ftplib
import machinekit
import machinetalk.protobuf.status_pb2 as STATUS

from MKCommand import *
from MKServiceCommand import *

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
    RemoteFilename = 'FreeCAD.ngc'

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
                #print(bs)

            self.ui.setTitleBarWidget(tb)

        self.job = None

        self.ui.load.clicked.connect(self.executeUpload)

        self.ui.run.clicked.connect(self.executeRun)
        self.ui.step.clicked.connect(self.executeStep)
        self.ui.pause.clicked.connect(self.executePause)
        self.ui.stop.clicked.connect(self.executeStop)

        self.ui.status.setText('')
        rect = self.ui.geometry()
        self.ui.resize(rect.width(), 0)

        self.observer = TreeSelectionObserver(self.objectSelectionChanged)
        FreeCADGui.Selection.addObserver(self.observer)
        self.objectSelectionChanged()

        #self.eventFilter = EventFilter()
        #self.ui.installEventFilter(self.eventFilter)

        self.updateJob()
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

    def remoteFilePath(self, path = None):
        if path is None:
            path = self.RemoteFilename
        return "%s/%s" % (self['status.config.remote_path'], path)

    def executeUpload(self):
        job = self.job
        if job:
            currTool = None
            postlist = []
            for obj in job.Operations.Group:
                tc = PathUtil.toolControllerForOp(obj)
                if tc is not None:
                    if tc.ToolNumber != currTool:
                        postlist.append(tc)
                        currTool = tc.ToolNumber
                postlist.append(obj)

            post = PathPost.CommandPathPost()
            (fail, gcode) = post.exportObjectsWith(postlist, job, False)
            if not fail:
                preamble = "(FreeCAD.Job: %s)\n(FreeCAD.File: %s)\n" % (job.Name, job.Document.FileName)
                buf = io.BytesIO((preamble + gcode).encode())
                endpoint = self.mk.endpoint.get('file')
                if endpoint:
                    ftp = ftplib.FTP()
                    ftp.connect(endpoint.address(), endpoint.port())
                    ftp.login()
                    ftp.storbinary("STOR %s" % self.RemoteFilename, buf)
                    ftp.quit()
                    sequence = machinekit.taskModeAuto(self)
                    sequence.append(MKCommandTaskReset(False))
                    sequence.append(MKCommandOpenFile(self.remoteFilePath(), False))
                    self.cmd.sendCommands(sequence)
                    self.mk.setJob(job)
                else:
                    print('No endpoint found')
            else:
                print('Post processing failed')

    def executeRun(self):
        sequence = machinekit.taskModeMDI(self)
        sequence.append(MKCommandTaskExecute('M6 T0'))
        sequence.append(MKCommandWaitUntil(lambda : self['status.io.tool.nr'] <= 0))
        sequence.extend(machinekit.taskModeAuto(self, True))
        sequence.append(MKCommandTaskRun(False))
        self.cmd.sendCommands(sequence)

    def executeStep(self):
        sequence = machinekit.taskModeAuto(self)
        sequence.append(MKCommandTaskStep())
        self.cmd.sendCommands(sequence)

    def executePause(self):
        if self.isPaused():
            self.cmd.sendCommand(MKCommandTaskResume())
        else:
            self.cmd.sendCommand(MKCommandTaskPause())

    def executeStop(self):
        self.cmd.sendCommand(MKCommandTaskAbort())

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

    def updateJob(self):
        title = '-.-'
        path = self['status.task.file']
        if path:
            title = path.split('/')[-1]
            if self.remoteFilePath() == path:
                buf = io.BytesIO()
                endpoint = self.mk.endpoint.get('file')
                if endpoint:
                    ftp = ftplib.FTP()
                    ftp.connect(endpoint.address(), endpoint.port())
                    ftp.login()
                    ftp.retrbinary("RETR %s" % self.RemoteFilename, buf.write)
                    ftp.quit()
                    buf.seek(0)
                    line1 = buf.readline().decode()
                    line2 = buf.readline().decode()
                    if line1.startswith('(FreeCAD.Job: ') and line2.startswith('(FreeCAD.File: '):
                        title    = line1[14:-2]
                        filename = line2[15:-2]
                        for docName, doc in FreeCAD.listDocuments().items():
                            if doc.FileName == filename:
                                job = doc.getObject(title)
                                if job:
                                    self.mk.setJob(job)
                                    title = job.Label
        self.title.setText(title)

    def changed(self, service, updated):
        if service.topicName() == 'status.task' and 'file' in updated:
            self.updateJob()
        self.updateUI()
