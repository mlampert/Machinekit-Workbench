# Dock widget for jogging, including touching off and setting work coordinates

import FreeCAD
import FreeCADGui
import MKUtils
import PathScripts.PathGeom as PathGeom
import PathScripts.PathLog as PathLog
import PySide.QtCore
import PySide.QtGui
import machinekit
import machinetalk.protobuf.status_pb2 as STATUS
import machinetalk.protobuf.types_pb2 as TYPES

from MKCommand import *

PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())
#PathLog.trackModule(PathLog.thisModule())

Tolerance = 0.01

EmcLinearUnits = {
        STATUS.LINEAR_UNITS_INCH : 'in',
        STATUS.LINEAR_UNITS_MM   : 'mm',
        STATUS.LINEAR_UNITS_CM   : 'cm'
        }

class Jog(object):
    '''Dock widget to control jogging and work coordinate offset.'''
    JogContinuous = 'Continuous'

    def __init__(self, mk):
        PathLog.track()
        self.mk = mk
        self.ui = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('jog.ui'))
        palette = PySide.QtGui.QPalette()
        palette.setColor(PySide.QtGui.QPalette.Background, PySide.QtGui.QColor(0xffd75e))
        self.ui.dockWidgetContents.setAutoFillBackground(True)
        self.ui.dockWidgetContents.setPalette(palette)

        def setupJogButton(b, axes, icon, slot=None):
            b.setIcon(machinekit.IconResource(icon))
            b.setText('')
            if slot:
                b.clicked.connect(slot)
            else:
                b.clicked.connect(lambda  : self.jogAxes(axes))
                b.pressed.connect(lambda  : self.jogAxesBegin(axes))
                b.released.connect(lambda : self.jogAxesEnd(axes))

        def setupSetButton(b, axes, widget, width):
            b.setMaximumWidth(width)
            b.clicked.connect(lambda : self.setPosition(axes, widget))

        setupJogButton(self.ui.jogN,   'Y', 'arrow-up.svg')
        setupJogButton(self.ui.jogNE, 'XY', 'arrow-right-up.svg')
        setupJogButton(self.ui.jogE,   'X', 'arrow-right.svg')
        setupJogButton(self.ui.jogSE, 'Xy', 'arrow-right-down.svg')
        setupJogButton(self.ui.jogS,   'y', 'arrow-down.svg')
        setupJogButton(self.ui.jogSW, 'xy', 'arrow-left-down.svg')
        setupJogButton(self.ui.jogW,   'x', 'arrow-left.svg')
        setupJogButton(self.ui.jogNW, 'xY', 'arrow-left-up.svg')
        setupJogButton(self.ui.jogU,   'Z', 'arrow-up.svg')
        setupJogButton(self.ui.jogD,   'z', 'arrow-down.svg')
        setupJogButton(self.ui.jog0,    '', 'home-xy.svg', lambda : self.jogAxesZero('-'))
        setupJogButton(self.ui.jogZ0,   '', 'home-z.svg',  lambda : self.jogAxesZero('|'))
        setupJogButton(self.ui.jogStop, '', 'stop.svg',    lambda : self.jogAxesStop())

        buttonWidth = self.ui.setX.size().height()
        setupSetButton(self.ui.setX,      'x', self.ui.posX, buttonWidth)
        setupSetButton(self.ui.setY,      'y', self.ui.posY, buttonWidth)
        setupSetButton(self.ui.setZ,      'z', self.ui.posZ, buttonWidth)
        setupSetButton(self.ui.setX0,     'x',         None, buttonWidth)
        setupSetButton(self.ui.setY0,     'y',         None, buttonWidth)
        setupSetButton(self.ui.setZ0,     'z',         None, buttonWidth)
        setupSetButton(self.ui.setXYZ0, 'xyz',         None, buttonWidth)
        self.ui.jogStop.setIconSize(PySide.QtCore.QSize(3 * buttonWidth, 3 * buttonWidth))

        self.jogGoto = None
        self.ui.jogScan.clicked.connect(lambda : self.scanJob(True))
        self.ui.jogScanBackwards.clicked.connect(lambda : self.scanJob(False))

        FreeCADGui.Selection.addObserver(self)

        self.isSetup = False
        self.updateUI()

        self.mk.statusUpdate.connect(self.changed)
        machinekit.jog = self

    def terminate(self):
        '''Remove receiver from FC's UI.'''
        PathLog.track()
        self.mk.statusUpdate.disconnect(self.changed)
        self.mk = None
        FreeCADGui.Selection.removeObserver(self)
        if machinekit.jog == self:
            machinekit.jog = None

    def setupUI(self):
        PathLog.track()
        for inc in [self.JogContinuous] + self.mk['status.config.increments']:
            item = PySide.QtGui.QListWidgetItem(inc.strip())
            item.setTextAlignment(PySide.QtCore.Qt.AlignRight)
            self.ui.jogDistance.addItem(item)
        self.ui.jogDistance.setCurrentRow(0)
        self.isSetup = True

    def isConnected(self, topics=None):
        '''Return true if MK is connected and responsive.'''
        PathLog.track()
        return self.mk.isValid()

    def setPosition(self, label, widget):
        '''Set the working position of one or more axes.'''
        PathLog.track()
        commands = MKUtils.taskModeMDI(self.mk)

        cmds = ['G10', 'L20', 'P0']
        for l in label:
            value = 0 if widget is None else widget.value()
            offset = self.mk["status.motion.offset.g5x.%s" % l]
            PathLog.debug("set pos[%s]=%.2f  (%.2f)" % (l, value, offset))
            cmds.append("%s%g" % (l, value))
        code = ' '.join(cmds)
        PathLog.debug("set pos-%s: '%s'" % (label, code))
        commands.append(MKCommandTaskExecute(code))

        self.mk['command'].sendCommands(commands)

    def joggingVelocity(self, axis):
        '''Return the velocity to be used for jogging the given axis as defined by MK.'''
        PathLog.track()
        return self.mk['status.config.velocity.linear.default']

    def getJogIndexAndVelocity(self, axis):
        '''Return a tuple of the given axis' index and velocity according to MK.'''
        PathLog.track()
        if axis in machinekit.AxesForward:
            index = machinekit.AxesForward.index(axis)
            veloc = self.joggingVelocity(axis)
        if axis in machinekit.AxesBackward:
            index = machinekit.AxesBackward.index(axis)
            veloc = 0.0 - self.joggingVelocity(axis)
        return (index, veloc)

    def displayPos(self, axis):
        '''Return the tools position as it should be displayed.'''
        PathLog.track()
        return self.mk["status.motion.position.actual.%s" % axis] - self.mk["status.motion.offset.g5x.%s" % axis]

    def jogContinuously(self):
        '''Return True if the user wants to jog continously.'''
        PathLog.track()
        return self.ui.jogDistance.currentRow() == 0

    def jogAxesZero(self, axes):
        '''jogAxesZero(axes) ... jog each of the specified axes to its 0 position.
        Note that no velocity adaption is going on so if two or more axis are specified
        each will reach its destination in its own time regardless of the progress of
        the other axes.'''
        PathLog.track()
        PathLog.track(axes)
        jog = []
        for axis in (['x', 'y'] if axes[0] == '-' else ['z']):
            distance = self.displayPos(axis)
            if distance != 0.0:
                index, velocity = self.getJogIndexAndVelocity(axis)
                jog.append(MKCommandAxisJog(index,  velocity,  distance))
        if jog:
            sequence = [[cmd] for cmd in MKUtils.taskModeManual(self.mk)]
            sequence.append(jog)
            self.mk['command'].sendCommandSequence(sequence)

    def jogAxes(self, axes):
        '''jogAxes(axes) ... initiate a jog of all specified axes according to the current settings.'''
        PathLog.track(axes)
        if not self.jogContinuously():
            jog = []
            for axis in axes:
                index, velocity = self.getJogIndexAndVelocity(axis)
                units = EmcLinearUnits[self.mk['status.config.units.linear']]
                distance = FreeCAD.Units.Quantity(self.ui.jogDistance.currentItem().text()).getValueAs(units)
                jog.append(MKCommandAxisJog(index, velocity, distance))
            if jog:
                sequence = [[cmd] for cmd in MKUtils.taskModeManual(self.mk)]
                sequence.append(jog)
                self.mk['command'].sendCommandSequence(sequence)

    def jogAxesBegin(self, axes):
        '''Calback when the user presses one of the jog buttons - if continuous jogging
        is configured this starts the jog.'''
        PathLog.track(axes)
        if self.jogContinuously():
            jog = []
            for axis in axes:
                index, velocity = self.getJogIndexAndVelocity(axis)
                jog.append(MKCommandAxisJog(index,  velocity))
            if jog:
                sequence = [[cmd] for cmd in MKUtils.taskModeManual(self.mk)]
                sequence.append(jog)
                self.mk['command'].sendCommandSequence(sequence)


    def jogAxesEnd(self, axes):
        '''Calback when the user releases one of the jog buttons - if continuous jogging
        is configured this ends the jog.'''
        PathLog.track(axes)
        if self.jogContinuously():
            jog = []
            for axis in axes:
                index, velocity = self.getJogIndexAndVelocity(axis)
                jog.append(MKCommandAxisAbort(index))
            if jog:
                sequence = [[cmd] for cmd in MKUtils.taskModeManual(self.mk)]
                sequence.append(jog)
                self.mk['command'].sendCommandSequence(sequence)

    def jogAxesStop(self):
        '''Explicitly stop all jog motions currently in progress.'''
        PathLog.track()
        sequence = [[cmd] for cmd in MKUtils.taskModeManual(self.mk)]
        sequence.append([MKCommandAxisAbort(i) for i in range(3)])
        self.mk['command'].abortCommandSequence()
        self.mk['command'].sendCommandSequence(sequence)

    def _jogXYCmdsFromTo(self, start, end):
        jog = []
        if not PathGeom.isRoughly(start.x, end.x, Tolerance):
            index, velocity = self.getJogIndexAndVelocity('x')
            PathLog.info("jog x from %.2f to %.2f (%d, %.2f, %.2f)" % (start.x, end.x, index, velocity, start.x - end.x))
            jog.append(MKCommandAxisJog(index, velocity, start.x - end.x))
        if not PathGeom.isRoughly(start.y, end.y, Tolerance):
            index, velocity = self.getJogIndexAndVelocity('y')
            PathLog.info("jog y from %.2f to %.2f (%d, %.2f, %.2f)" % (start.y, end.y, index, velocity, start.y - end.y))
            jog.append(MKCommandAxisJog(index, velocity, start.y - end.y))
        return jog

    # Selection.Observer
    def addSelection(self, doc, obj, sub, pnt):
        '''FC callback if the selection in the 3d view changes - used to determine the destination
        when the user wants to jog the tool to a specific position.'''
        PathLog.track()
        if self.ui.jogGoto.isChecked() and self.mk['status.motion.state'] == TYPES.RCS_DONE:
            x = pnt[0]
            y = pnt[1]
            z = pnt[2]
            mkx = self.displayPos('x')
            mky = self.displayPos('y')
            mkz = self.displayPos('z')
            if PathGeom.isRoughly(x, mkx, Tolerance) and PathGeom.isRoughly(y, mky, Tolerance):
                if not PathGeom.isRoughly(z, mkz, Tolerance):
                    # only jog the Z axis if XY already match
                    index, velocity = self.getJogIndexAndVelocity('z')
                    jog = [MKCommandAxisJog(index, velocity, mkz - z)]
                    PathLog.debug("jog z from %.2f to %.2f" % (mkz, z))
                else:
                    jog = None
                    PathLog.debug("z already aligned (%.2f), no jogging required" % z)
            else:
                # by default we just jog X & Y
                jog = self._jogXYCmdsFromTo(FreeCAD.Vector(mkx, mky, 0), FreeCAD.Vector(x, y, 0))

            sequence = [[cmd] for cmd in MKUtils.taskModeManual(self.mk)]
            sequence.append(jog)
            self.mk['command'].sendCommandSequence(sequence)

    def updateDRO(self, connected, powered):
        '''Callback invoked whenever the position or the work offset changed.'''
        PathLog.track()
        def updateAxisWidget(w, pos, homed):
            if homed == 0:
                w.setStyleSheet('color:blueviolet; background-color:lightGray')
            else:
                w.setStyleSheet('color:darkgreen; background-color:white')
            w.setValue(pos)

        if connected and powered:
            actual = self.mk['status.motion.position.actual']
            off = self.mk['status.motion.offset.g5x']
            axis = self.mk['status.motion.axis']
            updateAxisWidget(self.ui.posX, actual['x'] - off['x'], axis[0].homed)
            updateAxisWidget(self.ui.posY, actual['y'] - off['y'], axis[1].homed)
            updateAxisWidget(self.ui.posZ, actual['z'] - off['z'], axis[2].homed)

    def updateUI(self):
        '''Callback invoked on any changes to update the view.'''
        PathLog.track()
        connected = self.isConnected()
        powered = self.mk.isPowered()
        isIdle = self.mk['status.interp.state'] == STATUS.EMC_TASK_INTERP_IDLE

        if connected:
            self.ui.setWindowTitle(self.mk['status.config.name'])
            if not self.isSetup:
                self.setupUI()

        self.ui.jogScan.setEnabled(not self.mk.getJob() is None)
        self.ui.jogScanBackwards.setEnabled(not self.mk.getJob() is None)

        self.updateDRO(connected, powered)
        self.ui.dockWidgetContents.setEnabled(powered and isIdle)


    def changed(self, service, msg):
        '''Callback invoked whenever MK sent an update.'''
        PathLog.track(service, msg)
        if self.mk:
            if 'status' in service.topicName():
                self.updateUI()

    def scanJob(self, forward):
        '''scanJob(forward) ... move the tool around the outer perimeter of the job.'''
        PathLog.track()
        job = self.mk.getJob()
        if job and hasattr(job, 'Path') and job.Path:
            bb = job.Path.BoundBox
            if bb.isValid():
                off = self.mk['status.motion.offset.g5x']
                bb.move(FreeCAD.Vector(off['x'], off['y'], off['z']))
                if self.mk.boundBox().isInside(bb):
                    mkx = self.displayPos('x')
                    mky = self.displayPos('y')
                    begin = FreeCAD.Vector(mkx, mky, 0)
                    pts = []
                    bb = job.Path.BoundBox
                    if forward:
                        pts.append(FreeCAD.Vector(bb.XMin, bb.YMin, 0))
                        pts.append(FreeCAD.Vector(bb.XMax, bb.YMin, 0))
                        pts.append(FreeCAD.Vector(bb.XMax, bb.YMax, 0))
                        pts.append(FreeCAD.Vector(bb.XMin, bb.YMax, 0))
                    else:
                        pts.append(FreeCAD.Vector(bb.XMin, bb.YMin, 0))
                        pts.append(FreeCAD.Vector(bb.XMin, bb.YMax, 0))
                        pts.append(FreeCAD.Vector(bb.XMax, bb.YMax, 0))
                        pts.append(FreeCAD.Vector(bb.XMax, bb.YMin, 0))

                    dist = [begin.distanceToPoint(p) for p in pts]
                    rot = dist.index(min(dist))
                    pts = pts[rot:] + pts[:rot]
                    pts.append(pts[0])
                    PathLog.info(" begin = (%5.2f, %5.2f)" % (begin.x, begin.y))
                    for i, p in enumerate(pts):
                        PathLog.info(" pts[%d] = (%5.2f, %5.2f)" % (i, p.x, p.y))

                    jog = []
                    if not PathGeom.pointsCoincide(begin, pts[0]):
                        PathLog.info("Move to start point (%.2f, %.2f)" % (pts[0].x, pts[0].y))
                        jog.append(self._jogXYCmdsFromTo(begin, pts[0]))
                    for i, j in zip(pts, pts[1:]):
                        jog.append(self._jogXYCmdsFromTo(i, j))

                    sequence = [[cmd] for cmd in MKUtils.taskModeManual(self.mk)]
                    sequence.extend(jog)
                    self.mk['command'].sendCommandSequence(sequence)
                else:
                    mbb = self.mk.boundBox()
                    msg = ["Cannot scan job!"]
                    if mbb.XMin > bb.XMin:
                        msg.append("X limit min exceeded by: %.2f" % (mbb.XMin - bb.XMin))
                    if mbb.XMax < bb.XMax:
                        msg.append("X limit max exceeded by: %.2f" % (bb.XMax - mbb.XMax))
                    if mbb.YMin > bb.YMin:
                        msg.append("Y limit min exceeded by: %.2f" % (mbb.YMin - bb.YMin))
                    if mbb.YMax < bb.YMax:
                        msg.append("Y limit max exceeded by: %.2f" % (bb.YMax - mbb.YMax))
                    if mbb.ZMin > bb.ZMin:
                        msg.append("Z limit min exceeded by: %.2f" % (mbb.ZMin - bb.ZMin))
                    if mbb.ZMax < bb.ZMax:
                        msg.append("Z limit max exceeded by: %.2f" % (bb.ZMax - mbb.ZMax))

                    mb = PySide.QtGui.QMessageBox()
                    mb.setWindowIcon(machinekit.IconResource('machinekiticon.png'))
                    mb.setWindowTitle('Machinekit')
                    mb.setTextFormat(PySide.QtCore.Qt.TextFormat.RichText)
                    mb.setText("<div align='center'>%s</div>" % '<br/>'.join(msg))
                    mb.setIcon(PySide.QtGui.QMessageBox.Critical)
                    mb.setStandardButtons(PySide.QtGui.QMessageBox.Ok)
                    mb.exec_()
            else:
                PathLog.error("BoundBox of job %s is not valid" % job.Label)
        else:
            PathLog.error('No job uploaded for scanning')

