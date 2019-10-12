import FreeCAD
import FreeCADGui
import MKUtils
import MachinekitManualToolChange
import PathScripts.PathLog as PathLog
import PathScripts.PathPost as PathPost
import PathScripts.PathUtil as PathUtil
import PySide.QtCore
import PySide.QtGui
import ftplib
import io
import machinekit
import machinetalk.protobuf.motcmds_pb2 as MOTCMDS
import machinetalk.protobuf.status_pb2 as STATUS
import machinetalk.protobuf.types_pb2 as TYPES

from MKCommand import *
from MKServiceCommand import *


PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
PathLog.trackModule(PathLog.thisModule())

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
        palette = PySide.QtGui.QPalette()
        palette.setColor(PySide.QtGui.QPalette.Background, PySide.QtGui.QColor(0xffd75e))
        self.ui.dockWidgetContents.setAutoFillBackground(True)
        self.ui.dockWidgetContents.setPalette(palette)

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

            self.ui.setTitleBarWidget(tb)

        self.job = None

        self.ui.load.clicked.connect(self.executeUpload)

        self.ui.run.clicked.connect(self.executeRun)
        self.ui.step.clicked.connect(self.executeStep)
        self.ui.pause.clicked.connect(self.executePause)
        self.ui.stop.clicked.connect(self.executeStop)
        self.ui.scaleInt.valueChanged.connect(self.executeScaleInt)
        self.ui.scaleInt.sliderReleased.connect(self.executeScaleVal)
        self.ui.scaleVal.editingFinished.connect(self.executeScaleVal)

        self.ui.status.setText('')
        rect = self.ui.geometry()
        self.ui.resize(rect.width(), 0)

        self.observer = TreeSelectionObserver(self.objectSelectionChanged)
        FreeCADGui.Selection.addObserver(self.observer)
        self.objectSelectionChanged()

        #self.eventFilter = EventFilter()
        #self.ui.installEventFilter(self.eventFilter)

        self.updateOverride()
        self.updateJob()
        self.updateUI()
        self.toolChange = MachinekitManualToolChange.Controller(self.mk)
        machinekit.execute = self
        self.mk.statusUpdate.connect(self.changed)

    def terminate(self):
        self.mk.statusUpdate.disconnect(self.changed)
        self.mk = None
        FreeCADGui.Selection.removeObserver(self.observer)
        if machinekit.execute == self:
            machinekit.execute = None

    def isConnected(self, topics=None):
        return self.mk.isValid()

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
        return STATUS.EmcInterpStateType.Value(state) == self.mk['status.interp.state']

    def isIdle(self):
        return self.isState('EMC_TASK_INTERP_IDLE')
    def isPaused(self):
        return self.isState('EMC_TASK_INTERP_PAUSED')

    def remoteFilePath(self, path = None):
        if path is None:
            path = self.RemoteFilename
        return "%s/%s" % (self.mk['status.config.remote_path'], path)

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
            fail, gcode = post.exportObjectsWith(postlist, job, False)
            if not fail:
                print("POST: ", fail)
                preamble = "(FreeCAD.Job: %s)\n(FreeCAD.File: %s)\n(FreeCAD.Signature: %d)\n" % (job.Name, job.Document.FileName, MKUtils.pathSignature(job.Path))
                buf = io.BytesIO((preamble + gcode).encode())
                endpoint = self.mk.instance.endpoint.get('file')
                if endpoint:
                    ftp = ftplib.FTP()
                    ftp.connect(endpoint.address(), endpoint.port())
                    ftp.login()
                    ftp.storbinary("STOR %s" % self.RemoteFilename, buf)
                    ftp.quit()
                    sequence = MKUtils.taskModeMDI(self.mk)
                    for tc in job.ToolController:
                        t = tc.Tool
                        sequence.append(MKCommandTaskExecute("G10L1P%dR%gZ%f" % (tc.ToolNumber, t.Diameter/2., t.LengthOffset)))
                    sequence.extend(MKUtils.taskModeAuto(self.mk))
                    sequence.append(MKCommandTaskReset(False))
                    sequence.append(MKCommandOpenFile(self.remoteFilePath(), False))
                    self.mk['command'].sendCommands(sequence)
                    self.mk.setJob(job)
                else:
                    PathLog.error('No endpoint found')
            else:
                PathLog.error('Post processing failed')

    def executeRun(self):
        sequence = MKUtils.taskModeMDI(self.mk)
        sequence.append(MKCommandTaskExecute('M6 T0'))
        sequence.append(MKCommandWaitUntil(lambda : self.mk['status.io.tool.nr'] <= 0))
        sequence.extend(MKUtils.taskModeAuto(self.mk, True))
        sequence.append(MKCommandTaskRun(False))
        self.mk['command'].sendCommands(sequence)

    def executeStep(self):
        sequence = MKUtils.taskModeAuto(self.mk)
        sequence.append(MKCommandTaskStep())
        self.mk['command'].sendCommands(sequence)

    def executePause(self):
        if self.isPaused():
            self.mk['command'].sendCommand(MKCommandTaskResume())
        else:
            self.mk['command'].sendCommand(MKCommandTaskPause())

    def executeStop(self):
        self.mk['command'].sendCommand(MKCommandTaskAbort())

    def executeScaleInt(self):
        percent = self.ui.scaleInt.value()
        scale = percent / 100.0
        self.ui.scaleVal.blockSignals(True)
        self.ui.scaleVal.setValue(scale)
        self.ui.scaleVal.blockSignals(False)

    def executeScaleVal(self):
        scale = self.ui.scaleVal.value()
        self.mk['command'].sendCommand(MKCommandTrajSetScale(scale))

    def updateExecute(self, connected, powered):
        if connected and powered:
            if self.isIdle():
                self.ui.load.setEnabled(not self.job is None)
                self.ui.run.setEnabled(self.mk['status.task.file'] != '')
                self.ui.step.setEnabled(self.mk['status.task.file'] != '')
                self.ui.pause.setEnabled(False)
                self.ui.stop.setEnabled(False)
            else:
                self.ui.load.setEnabled(False)
                self.ui.run.setEnabled(False)
                self.ui.step.setEnabled(self.mk['status.motion.type'] == MOTCMDS.MotionType.Value('_EMC_MOTION_TYPE_NONE'))
                self.ui.pause.setEnabled(True)
                if self.ui.pause.isChecked() != self.isPaused():
                    self.ui.pause.setChecked(self.isPaused())
                self.ui.stop.setEnabled(True)

            mode = TYPES.RCS_STATUS.Name(self.mk['status.motion.state']).split('_')[1].lower()
            state = ' '.join(STATUS.EmcTaskExecStateType.Name(self.mk['status.task.state']).split('_')[3:]).lower()
            if mode == 'auto':
                istate = STATUS.EmcInterpStateType.Name(self.mk['status.interp.state']).split('_')[3].lower()
                mode = "%s.%s" % (mode, istate)
            self.ui.status.setText("%s:%s (%d/%d)" % (mode, state, self.mk['status.motion.line'], self.mk['status.task.line.total']))

    def updateUI(self):
        connected = self.isConnected()
        powered = self.mk.isPowered()

        self.updateExecute(connected, powered)
        self.ui.dockWidgetContents.setEnabled(powered)
        self.ui.override.setEnabled(powered and connected and self.mk['status.motion.feed.override'])

    def updateOverride(self):
        self.ui.scaleInt.blockSignals(True)
        self.ui.scaleInt.setMinimum(self.mk['status.config.override.feed.min'] * 100)
        self.ui.scaleInt.setMaximum(self.mk['status.config.override.feed.max'] * 100)
        self.ui.scaleInt.setSliderPosition(self.mk['status.motion.feed.rate'] * 100)
        self.ui.scaleInt.blockSignals(False)

        self.ui.scaleVal.blockSignals(True)
        self.ui.scaleVal.setValue(self.mk['status.motion.feed.rate'])
        self.ui.scaleVal.blockSignals(False)

    def updateJob(self):
        title = '-.-'
        path = self.mk['status.task.file']
        if path:
            title = path.split('/')[-1]
            if self.remoteFilePath() == path:
                buf = io.BytesIO()
                endpoint = self.mk.instance.endpoint.get('file')
                if endpoint:
                    ftp = ftplib.FTP()
                    ftp.connect(endpoint.address(), endpoint.port())
                    ftp.login()
                    ftp.retrbinary("RETR %s" % self.RemoteFilename, buf.write)
                    ftp.quit()
                    buf.seek(0)
                    line1 = buf.readline().decode()
                    line2 = buf.readline().decode()
                    line3 = buf.readline().decode()
                    #PathLog.debug("Line 1: '%s'" % line1)
                    #PathLog.debug("Line 2: '%s'" % line2)
                    #PathLog.debug("Line 3: '%s'" % line3)
                    if line1.startswith('(FreeCAD.Job: ') and line2.startswith('(FreeCAD.File: ') and line3.startswith('(FreeCAD.Signature: '):
                        title     = line1[14:-2]
                        filename  = line2[15:-2]
                        signature = line3[20:-2]
                        PathLog.debug("Loaded document: '%s' - '%s'" % (filename, title))
                        for docName, doc in FreeCAD.listDocuments().items():
                            PathLog.debug("Document: '%s' - '%s'" % (docName, doc.FileName))
                            if doc.FileName == filename:
                                job = doc.getObject(title)
                                if job:
                                    sign = MKUtils.pathSignature(job.Path)
                                    if str(sign) == signature:
                                        self.mk.setJob(job)
                                        title = "%s.%s" % (job.Document.Label, job.Label)
                                        PathLog.info("Job %s.%s already loaded." % (docName, title))
                                    else:
                                        PathLog.info("Job %s.%s needs updating (%s vs. %s)" % (docName, title, signature, sign))
        self.title.setText(title)

    def changed(self, service, updated):
        if self.mk:
            if service.topicName() == 'status.task' and 'file' in updated:
                self.updateJob()

            if service.topicName() == 'status.motion' and 'feed.rate' in updated:
                self.updateOverride()

            self.updateUI()
