import FreeCAD
import FreeCADGui
import machinekit

from PySide import QtCore, QtGui

Dock = None

class MachinekitCommand(object):
    def __init__(self, services):
        self.services = services

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
        FreeCADGui.getMainWindow().removeDockWidget(dock.ui)
        dock.ui.deleteLater()

class MachinekitCommandJog(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__(['command', 'status', 'task', 'error'])

    def activate(self, instance):
        return machinekit.Jog(instance)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Jog',
                'ToolTip'   : 'Jog and DRO interface for machine setup'
                }

class MachinekitCommandExecute(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__(['command', 'status', 'task', 'error'])

    def activate(self, instance):
        return machinekit.Execute(instance)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Execute',
                'ToolTip'   : 'Interface for controlling file execution'
                }

ToolbarName = 'MachinekitTools'
ToolbarTools = ['MachinekitCommandJog', 'MachinekitCommandExecute']

def Activated():
    pass

def Deactivated():
    pass

FreeCADGui.addCommand('MachinekitCommandJog', MachinekitCommandJog())
FreeCADGui.addCommand('MachinekitCommandExecute', MachinekitCommandExecute())

