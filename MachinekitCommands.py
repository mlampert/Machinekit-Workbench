import FreeCAD
import FreeCADGui
import MachinekitJog
import machinekit

from PySide import QtCore, QtGui

Dock = None

class MachinekitCommand(object):
    def __init__(self, services):
        self.services = services

    def IsActive(self):
        return len(machinekit.Instances()) > 0

    def Activated(self):
        global Dock
        dock = None
        instances = machinekit.Instances(self.serviceNames())
        if 0 == len(instances):
            pass
        if 1 == len(instances):
            dock = self.activate(instances[0])
        if not dock is None:
            Dock = dock
            for closebutton in [widget for widget in dock.ui.children() if widget.objectName().endswith('closebutton')]:
                closebutton.clicked.connect(lambda : self.terminateDock(dock))
            FreeCADGui.getMainWindow().addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock.ui)

    def serviceNames(self):
        return self.services

    def terminateDock(self, dock):
        dock.terminate()
        FreeCADGui.getMainWindow().removeDockWidget(dock.ui)
        dock.ui.deleteLater()

class MachinekitCommandJog(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__(['command', 'status'])

    def activate(self, mk):
        return MachinekitJog.Jog(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Jog',
                'ToolTip'   : 'Jog and DRO interface for machine setup'
                }

class MachinekitCommandExecute(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__(['command', 'status'])

    def activate(self, mk):
        return machinekit.Execute(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Execute',
                'ToolTip'   : 'Interface for controlling file execution'
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
        if super(self.__class__, self).IsActive():
            mk = machinekit.Instances()[0]
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
ToolbarTools = ['MachinekitCommandJog', 'MachinekitCommandExecute']
MenuList     = ["MachinekitCommandEstop", "MachinekitCommandHome", "Separator"] + ToolbarTools

def Activated():
    pass

def Deactivated():
    pass

FreeCADGui.addCommand('MachinekitCommandEstop',   MachinekitCommandEstop())
FreeCADGui.addCommand('MachinekitCommandExecute', MachinekitCommandExecute())
FreeCADGui.addCommand('MachinekitCommandHome',    MachinekitCommandHome())
FreeCADGui.addCommand('MachinekitCommandJog',     MachinekitCommandJog())

