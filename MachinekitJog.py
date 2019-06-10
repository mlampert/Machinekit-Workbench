import FreeCAD
import FreeCADGui
import machinekit

from MKCommand import *

class Jog(object):
    def __init__(self, mk):
        machinekit.jog = self
        self.mk = mk
        self.ui = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('jog.ui'))

        self.connectors = []
        self.services = self.mk.connectServices(['command', 'status'])
        for service in self.services:
            if 'command' == service.name:
                self.cmd = service
            self.connectors.append(machinekit.ServiceConnector(service, self))

        def setupJogButton(b, axes, icon, zero=False):
            b.setIcon(machinekit.IconResource(icon))
            b.setText('')
            if zero:
                b.clicked.connect(lambda  : self.jogAxesZero(axes))
            else:
                b.clicked.connect(lambda  : self.jogAxes(axes))
                b.pressed.connect(lambda  : self.jogAxesBegin(axes))
                b.released.connect(lambda : self.jogAxesEnd(axes))

        def setupSetButton(b, axes, widget, width):
            b.setMaximumWidth(width)
            b.clicked.connect(lambda : self.setPosition(axes, widget))

        setupJogButton(self.ui.jogN,  'Y',  'arrow-up.svg')
        setupJogButton(self.ui.jogNE, 'XY', 'arrow-right-up.svg')
        setupJogButton(self.ui.jogE,  'X',  'arrow-right.svg')
        setupJogButton(self.ui.jogSE, 'Xy', 'arrow-right-down.svg')
        setupJogButton(self.ui.jogS,  'y',  'arrow-down.svg')
        setupJogButton(self.ui.jogSW, 'xy', 'arrow-left-down.svg')
        setupJogButton(self.ui.jogW,  'x',  'arrow-left.svg')
        setupJogButton(self.ui.jogNW, 'xY', 'arrow-left-up.svg')
        setupJogButton(self.ui.jogU,  'Z',  'arrow-up.svg')
        setupJogButton(self.ui.jogD,  'z',  'arrow-down.svg')
        setupJogButton(self.ui.jog0,  '-',  'home-xy.svg', True)
        setupJogButton(self.ui.jogZ0, '|',  'home-z.svg',  True)

        buttonWidth = self.ui.setX.size().height()
        setupSetButton(self.ui.setX,      'X', self.ui.posX, buttonWidth)
        setupSetButton(self.ui.setY,      'Y', self.ui.posY, buttonWidth)
        setupSetButton(self.ui.setZ,      'Z', self.ui.posZ, buttonWidth)
        setupSetButton(self.ui.setX0,     'X',         None, buttonWidth)
        setupSetButton(self.ui.setY0,     'Y',         None, buttonWidth)
        setupSetButton(self.ui.setZ0,     'Z',         None, buttonWidth)
        setupSetButton(self.ui.setXYZ0, 'XYZ',         None, buttonWidth)

    def __getitem__(self, index):
        path = index.split('.')
        for service in self.services:
            if service.name == path[0]:
                if len(path) > 1:
                    return service[path[1:]]
                return service
        return None

    def terminate(self):
        pass

    def isConnected(self, topics=None):
        if topics is None:
            topics = ['status.config', 'status.io', 'status.motion']

        for topic in topics:
            service = self[topic]
            if service is None or not service.isValid():
                return False
        return not self.cmd is None

    def setPosition(self, label, widget):
        commands = machinekit.taskModeMDI(self)

        cmds = ['G10', 'L20', 'P1']
        for l in label:
            cmds.append("%s%f" % (l, 0 if widget is None else widget.value()))
        code = ' '.join(cmds)
        commands.append(MKCommandTaskExecute(code))

        self.cmd.sendCommands(commands)

    def joggingVelocity(self, axis):
        return self['status.config.velocity.linear.max']

    def getJogIndexAndVelocity(self, axis):
        if axis in machinekit.AxesForward:
            index = machinekit.AxesForward.index(axis)
            veloc = self.joggingVelocity(axis)
        if axis in machinekit.AxesBackward:
            index = machinekit.AxesBackward.index(axis)
            veloc = 0.0 - self.joggingVelocity(axis)
        return (index, veloc)

    def displayPos(self, axis):
        return self["status.motion.position.actual.%s" % axis] - self["status.motion.offset.g5x.%s" % axis]

    def jogAxesZero(self, axes):
        jog = []
        for axis in (['x', 'y'] if axes[0] == '-' else ['z']):
            distance = self.displayPos(axis)
            if distance != 0.0:
                index, velocity = self.getJogIndexAndVelocity(axis)
                if distance < 0:
                    jog.append(MKCommandAxisJog(index, -velocity, -distance))
                else:
                    jog.append(MKCommandAxisJog(index,  velocity,  distance))
        if jog:
            sequence = [[cmd] for cmd in machinekit.taskModeManual(self)]
            sequence.append(jog)
            self.cmd.sendCommandSequence(sequence)

    def jogAxes(self, axes):
        if not self.ui.jogContinuous.isChecked():
            jog = []
            for axis in axes:
                index, velocity = self.getJogIndexAndVelocity(axis)
                distance = 5.0
                jog.append(MKCommandAxisJog(index, velocity, distance))
            if jog:
                sequence = [[cmd] for cmd in machinekit.taskModeManual(self)]
                sequence.append(jog)
                self.cmd.sendCommandSequence(sequence)

    def jogAxesBegin(self, axes):
        if self.ui.jogContinuous.isChecked():
            jog = []
            for axis in axes:
                index, velocity = self.getJogIndexAndVelocity(axis)
                jog.append(MKCommandAxisJog(index,  velocity))
            if jog:
                sequence = [[cmd] for cmd in machinekit.taskModeManual(self)]
                sequence.append(jog)
                self.cmd.sendCommandSequence(sequence)


    def jogAxesEnd(self, axes):
        if self.ui.jogContinuous.isChecked():
            jog = []
            for axis in axes:
                index, velocity = self.getJogIndexAndVelocity(axis)
                jog.append(MKCommandAxisAbort(index))
            if jog:
                sequence = [[cmd] for cmd in machinekit.taskModeManual(self)]
                sequence.append(jog)
                self.cmd.sendCommandSequence(sequence)
    def updateDRO(self, connected, powered):
        def updateAxisWidget(w, pos, homed):
            if homed:
                w.setStyleSheet('color:darkgreen; background-color:white')
            else:
                w.setStyleSheet('color:blueviolet; background-color:lightGray')
            w.setValue(pos)

        if connected and powered:
            actual = self['status.motion.position.actual']
            off = self['status.motion.offset.g5x']
            axis = self['status.motion.axis']
            updateAxisWidget(self.ui.posX, actual['x'] - off['x'], axis[0].homed)
            updateAxisWidget(self.ui.posY, actual['y'] - off['y'], axis[1].homed)
            updateAxisWidget(self.ui.posZ, actual['z'] - off['z'], axis[2].homed)

    def updateUI(self):
        connected = self.isConnected()
        powered = self.mk.isPowered()

        if connected:
            self.ui.setWindowTitle(self['status.config.name'])

        self.updateDRO(connected, powered)
        self.ui.dockWidgetContents.setEnabled(powered)


    def changed(self, service, msg):
        if 'status' in service.topicName():
            self.updateUI()

