import FreeCAD
import FreeCADGui
import MachinekitExecute
import MachinekitHud
import MachinekitJog
import PathScripts.PathLog as PathLog
import machinekit

from PySide import QtCore

PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())
#PathLog.trackModule(PathLog.thisModule())

Dock = None

class MachinekitCommand(object):
    def __init__(self, name, services):
        PathLog.track(services)
        self.name = name
        self.services = services

    def validMachinekit(self):
        mk = machinekit.Any()
        if mk and mk.isValid():
            return mk
        return None

    def IsActive(self):
        PathLog.track(self.name)
        return not self.validMachinekit() is None

    def Activated(self):
        global Dock
        PathLog.track(self.name)
        dock = None
        instances = machinekit.Instances(self.serviceNames())
        if 0 == len(instances):
            PathLog.debug('No machinekit instances found')
            pass
        if 1 == len(instances):
            dock = self.activate(instances[0])
        if dock is None:
            PathLog.debug('No dock to activate')
        else:
            PathLog.debug('Activate first found instance')
            Dock = dock
            for closebutton in [widget for widget in dock.ui.children() if widget.objectName().endswith('closebutton')]:
                closebutton.clicked.connect(lambda : self.terminateDock(dock))
            FreeCADGui.getMainWindow().addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock.ui)

    def serviceNames(self):
        return self.services

    def terminateDock(self, dock):
        PathLog.track()
        dock.terminate()
        FreeCADGui.getMainWindow().removeDockWidget(dock.ui)
        dock.ui.deleteLater()

class MachinekitCommandJog(MachinekitCommand):
    def __init__(self):
        PathLog.track()
        super(self.__class__, self).__init__('Jog', ['command', 'status'])

    def activate(self, mk):
        PathLog.track()
        return MachinekitJog.Jog(mk)

    def GetResources(self):
        PathLog.track()
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Jog',
                'ToolTip'   : 'Jog and DRO interface for machine setup'
                }

class MachinekitCommandExecute(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__('Exe', ['command', 'status'])

    def activate(self, mk):
        return MachinekitExecute.Execute(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Execute',
                'ToolTip'   : 'Interface for controlling file execution'
                }

class MachinekitCommandHud(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__('Hud', ['command', 'status'])

    def IsActive(self):
        PathLog.track(self.name)
        return not (self.validMachinekit() is None or FreeCADGui.ActiveDocument is None)

    def activate(self, mk):
        MachinekitHud.ToggleHud(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Hud',
                'ToolTip'   : 'HUD DRO interface for machine setup'
                }


class MachinekitCommandPower(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__('Pwr', ['command', 'status'])

    def activate(self, mk):
        machinekit.Power(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Power',
                'ToolTip'   : 'Turn machinekit controller on/off'
                }

class MachinekitCommandHome(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__('Home', ['command', 'status'])

    def IsActive(self):
        PathLog.track(self.name)
        mk = self.validMachinekit()
        if mk:
            return mk.isPowered() and not mk.isHomed()
        return False

    def activate(self, mk):
        machinekit.Home(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Home',
                'ToolTip'   : 'Home all axes'
                }

ToolbarName  = 'MachinekitTools'
ToolbarTools = ['MachinekitCommandHud', 'MachinekitCommandJog', 'MachinekitCommandExecute']
MenuList     = ['MachinekitCommandPower', 'MachinekitCommandHome', 'Separator'] + ToolbarTools

class MachinekitCommandCenter(object):
    def __init__(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)
        self.commands = []

        self._addCommand('MachinekitCommandPower',   MachinekitCommandPower())
        self._addCommand('MachinekitCommandHome',    MachinekitCommandHome())
        self._addCommand('MachinekitCommandHud',     MachinekitCommandHud())
        self._addCommand('MachinekitCommandJog',     MachinekitCommandJog())
        self._addCommand('MachinekitCommandExecute', MachinekitCommandExecute())

        self.active = [cmd.IsActive() for cmd in self.commands]

    def _addCommand(self, name, cmd):
        self.commands.append(cmd)
        FreeCADGui.addCommand(name, cmd)

    def start(self):
        # it's probably good enough to update once a second
        self.timer.start(1000)

    def stop(self):
        self.timer.stop()

    def tick(self):
        active = [cmd.IsActive() for cmd in self.commands]
        def aString(activation):
            return '.'.join(['1' if a else '0' for a in activation])
        if self.active != active:
            PathLog.info("Command activation changed from %s to %s" % (aString(self.active), aString(active)))
            FreeCADGui.updateCommands()
            self.active = active

_commandCenter = MachinekitCommandCenter()

def Activated():
    PathLog.track()
    machinekit.Start()
    _commandCenter.start()

def Deactivated():
    PathLog.track()
    _commandCenter.stop()

