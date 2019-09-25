import FreeCAD
import FreeCADGui
import MachinekitExecute
import MachinekitHud
import MachinekitJog
import PathScripts.PathLog as PathLog
import machinekit

from PySide import QtCore, QtGui

PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
PathLog.trackModule(PathLog.thisModule())

Dock = None

class MachinekitCommand(object):
    def __init__(self, services):
        PathLog.track(services)
        self.services = services

    def IsActive(self):
        return not machinekit.Any() is None

    def Activated(self):
        global Dock
        dock = None
        instances = machinekit.Instances(self.serviceNames())
        if 0 == len(instances):
            PathLog.debug('No machinekit instances found')
            pass
        if 1 == len(instances):
            dock = self.activate(instances[0])
        if not dock is None:
            PathLog.debug('Activate first found instance')
            Dock = dock
            for closebutton in [widget for widget in dock.ui.children() if widget.objectName().endswith('closebutton')]:
                closebutton.clicked.connect(lambda : self.terminateDock(dock))
            FreeCADGui.getMainWindow().addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock.ui)
        else:
            PathLog.debug('No dock to activate')

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
        super(self.__class__, self).__init__(['command', 'status'])

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
        super(self.__class__, self).__init__(['command', 'status'])

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
        super(self.__class__, self).__init__(['command', 'status'])

    def IsActive(self):
        if super(self.__class__, self).IsActive():
            return not FreeCADGui.ActiveDocument is None
        return False

    def activate(self, mk):
        MachinekitHud.ToggleHud(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Hud',
                'ToolTip'   : 'HUD DRO interface for machine setup'
                }


class MachinekitCommandEstop(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__(['command', 'status'])

    def activate(self, mk):
        machinekit.Estop(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Power',
                'ToolTip'   : 'Turn machinekit controller on/off'
                }

class MachinekitCommandHome(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__(['command', 'status'])

    def IsActive(self):
        mk = machinekit.Any()
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
MenuList     = ["MachinekitCommandEstop", "MachinekitCommandHome", "Separator"] + ToolbarTools

def Activated():
    PathLog.track()
    machinekit.Start()

def Deactivated():
    PathLog.track()
    pass

FreeCADGui.addCommand('MachinekitCommandEstop',   MachinekitCommandEstop())
FreeCADGui.addCommand('MachinekitCommandExecute', MachinekitCommandExecute())
FreeCADGui.addCommand('MachinekitCommandHome',    MachinekitCommandHome())
FreeCADGui.addCommand('MachinekitCommandHud',     MachinekitCommandHud())
FreeCADGui.addCommand('MachinekitCommandJog',     MachinekitCommandJog())

