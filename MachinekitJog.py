import FreeCAD
import FreeCADGui
import PathScripts.PathGeom as PathGeom
import PathScripts.PathLog as PathLog
import PySide.QtCore
import PySide.QtGui
import machinekit
import machinetalk.protobuf.status_pb2 as STATUS

from MKCommand import *

PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
PathLog.trackModule(PathLog.thisModule())

EmcLinearUnits = {
        STATUS.EmcLinearUnitsType.Value('LINEAR_UNITS_INCH') : 'in',
        STATUS.EmcLinearUnitsType.Value('LINEAR_UNITS_MM')   : 'mm',
        STATUS.EmcLinearUnitsType.Value('LINEAR_UNITS_CM')   : 'cm'
        }

class Jog(object):
    JogContinuous = 'Continuous'

    def __init__(self, mk):
        PathLog.track()
        machinekit.jog = self
        self.mk = mk
        self.ui = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('jog.ui'))
        palette = PySide.QtGui.QPalette()
        palette.setColor(PySide.QtGui.QPalette.Background, PySide.QtGui.QColor(0xffd75e))
        self.ui.dockWidgetContents.setAutoFillBackground(True)
        self.ui.dockWidgetContents.setPalette(palette)

        self.connectors = []
        self.services = self.mk.connectServices(['command', 'status'])
        for service in self.services:
            if 'command' == service.name:
                self.cmd = service
            self.connectors.append(machinekit.ServiceConnector(service, self))

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
        setupSetButton(self.ui.setX,      'X', self.ui.posX, buttonWidth)
        setupSetButton(self.ui.setY,      'Y', self.ui.posY, buttonWidth)
        setupSetButton(self.ui.setZ,      'Z', self.ui.posZ, buttonWidth)
        setupSetButton(self.ui.setX0,     'X',         None, buttonWidth)
        setupSetButton(self.ui.setY0,     'Y',         None, buttonWidth)
        setupSetButton(self.ui.setZ0,     'Z',         None, buttonWidth)
        setupSetButton(self.ui.setXYZ0, 'XYZ',         None, buttonWidth)
        self.ui.jogStop.setIconSize(PySide.QtCore.QSize(3 * buttonWidth, 3 * buttonWidth))

        self.jogGoto = None

        FreeCADGui.Selection.addObserver(self)

        if self.isConnected():
            self.setupUI()
        else:
            self.isSetup = False

    def setupUI(self):
        PathLog.track()
        for inc in [self.JogContinuous] + self['status.config.increments']:
            item = PySide.QtGui.QListWidgetItem(inc.strip())
            item.setTextAlignment(PySide.QtCore.Qt.AlignRight)
            self.ui.jogDistance.addItem(item)
        self.ui.jogDistance.setCurrentRow(0)
        self.isSetup = True

    def __getitem__(self, index):
        PathLog.track()
        path = index.split('.')
        for service in self.services:
            if service.name == path[0]:
                if len(path) > 1:
                    return service[path[1:]]
                return service
        return None

    def terminate(self):
        PathLog.track()
        self.mk = None
        FreeCADGui.Selection.removeObserver(self)
        for connector in self.connectors:
            connector.separate()
        self.connectors = []

    def isConnected(self, topics=None):
        PathLog.track()
        if topics is None:
            topics = ['status.config', 'status.io', 'status.motion']

        for topic in topics:
            service = self[topic]
            if service is None or not service.isValid():
                return False
        return not self.cmd is None

    def setPosition(self, label, widget):
        PathLog.track()
        commands = machinekit.taskModeMDI(self)

        cmds = ['G10', 'L20', 'P1']
        for l in label:
            cmds.append("%s%f" % (l, 0 if widget is None else widget.value()))
        code = ' '.join(cmds)
        commands.append(MKCommandTaskExecute(code))

        self.cmd.sendCommands(commands)

    def joggingVelocity(self, axis):
        PathLog.track()
        return self['status.config.velocity.linear.max']

    def getJogIndexAndVelocity(self, axis):
        PathLog.track()
        if axis in machinekit.AxesForward:
            index = machinekit.AxesForward.index(axis)
            veloc = self.joggingVelocity(axis)
        if axis in machinekit.AxesBackward:
            index = machinekit.AxesBackward.index(axis)
            veloc = 0.0 - self.joggingVelocity(axis)
        return (index, veloc)

    def displayPos(self, axis):
        PathLog.track()
        return self["status.motion.position.actual.%s" % axis] - self["status.motion.offset.g5x.%s" % axis]

    def jogContinuously(self):
        PathLog.track()
        return self.ui.jogDistance.currentRow() == 0

    def jogAxesZero(self, axes):
        PathLog.track()
        PathLog.track(axes)
        jog = []
        for axis in (['x', 'y'] if axes[0] == '-' else ['z']):
            distance = self.displayPos(axis)
            if distance != 0.0:
                index, velocity = self.getJogIndexAndVelocity(axis)
                jog.append(MKCommandAxisJog(index,  velocity,  distance))
        if jog:
            sequence = [[cmd] for cmd in machinekit.taskModeManual(self)]
            sequence.append(jog)
            self.cmd.sendCommandSequence(sequence)

    def jogAxes(self, axes):
        PathLog.track(axes)
        if not self.jogContinuously():
            jog = []
            for axis in axes:
                index, velocity = self.getJogIndexAndVelocity(axis)
                units = EmcLinearUnits[self['status.config.units.linear']]
                distance = FreeCAD.Units.Quantity(self.ui.jogDistance.currentItem().text()).getValueAs(units)
                jog.append(MKCommandAxisJog(index, velocity, distance))
            if jog:
                sequence = [[cmd] for cmd in machinekit.taskModeManual(self)]
                sequence.append(jog)
                self.cmd.sendCommandSequence(sequence)

    def jogAxesBegin(self, axes):
        PathLog.track(axes)
        if self.jogContinuously():
            jog = []
            for axis in axes:
                index, velocity = self.getJogIndexAndVelocity(axis)
                jog.append(MKCommandAxisJog(index,  velocity))
            if jog:
                sequence = [[cmd] for cmd in machinekit.taskModeManual(self)]
                sequence.append(jog)
                self.cmd.sendCommandSequence(sequence)


    def jogAxesEnd(self, axes):
        PathLog.track(axes)
        if self.jogContinuously():
            jog = []
            for axis in axes:
                index, velocity = self.getJogIndexAndVelocity(axis)
                jog.append(MKCommandAxisAbort(index))
            if jog:
                sequence = [[cmd] for cmd in machinekit.taskModeManual(self)]
                sequence.append(jog)
                self.cmd.sendCommandSequence(sequence)

    def jogAxesStop(self):
        PathLog.track()
        sequence = [[cmd] for cmd in machinekit.taskModeManual(self)]
        sequence.append([MKCommandAxisAbort(i) for i in range(3)])
        self.cmd.sendCommandSequence(sequence)

    # Selection.Observer
    def addSelection(self, doc, obj, sub, pnt):
        PathLog.track()
        if self.ui.jogGoto.isChecked():
            x = pnt[0]
            y = pnt[1]
            z = pnt[2]
            mkx = self.displayPos('x')
            mky = self.displayPos('y')
            mkz = self.displayPos('z')
            jog = []
            if PathGeom.isRoughly(x, mkx) and PathGeom.isRoughly(y, mky):
                # only jog the Z axis if XY already match
                index, velocity = self.getJogIndexAndVelocity('z')
                jog.append(MKCommandAxisJog(index, velocity, mkz - z))
            else:
                # by default we just jog X & Y
                index, velocity = self.getJogIndexAndVelocity('x')
                jog.append(MKCommandAxisJog(index, velocity, mkx - x))
                index, velocity = self.getJogIndexAndVelocity('y')
                jog.append(MKCommandAxisJog(index, velocity, mky - y))

            sequence = [[cmd] for cmd in machinekit.taskModeManual(self)]
            sequence.append(jog)
            self.cmd.sendCommandSequence(sequence)

    def updateDRO(self, connected, powered):
        PathLog.track()
        def updateAxisWidget(w, pos, homed):
            if homed == 0:
                w.setStyleSheet('color:blueviolet; background-color:lightGray')
            else:
                w.setStyleSheet('color:darkgreen; background-color:white')
            w.setValue(pos)

        if connected and powered:
            actual = self['status.motion.position.actual']
            off = self['status.motion.offset.g5x']
            axis = self['status.motion.axis']
            updateAxisWidget(self.ui.posX, actual['x'] - off['x'], axis[0].homed)
            updateAxisWidget(self.ui.posY, actual['y'] - off['y'], axis[1].homed)
            updateAxisWidget(self.ui.posZ, actual['z'] - off['z'], axis[2].homed)

    def updateUI(self):
        PathLog.track()
        connected = self.isConnected()
        powered = self.mk.isPowered()
        isIdle = self['status.interp.state'] == STATUS.EmcInterpStateType.Value('EMC_TASK_INTERP_IDLE')

        if connected:
            self.ui.setWindowTitle(self['status.config.name'])
            if not self.isSetup:
                self.setupUI()

        self.updateDRO(connected, powered)
        self.ui.dockWidgetContents.setEnabled(powered and isIdle)


    def changed(self, service, msg):
        PathLog.track(service, msg)
        if self.mk:
            if 'status' in service.topicName():
                self.updateUI()

