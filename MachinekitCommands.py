import FreeCAD
import FreeCADGui
import machinekit

from PySide import QtCore, QtGui

class MachinekitCommand(object):
    def __init__(self, services):
        self.services = services

    def Activated(self):
        dock = None
        instances = machinekit.Instances(self.serviceNames())
        if 0 == len(instances):
            pass
        if 1 == len(instances):
            dock = self.activate(instances[0])
        if not dock is None:
            FreeCADGui.getMainWindow().addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock.ui)

    def serviceNames(self):
        return self.services

class MachinekitCommandJog(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__(['command', 'status', 'task', 'error'])

    def activate(self, instance):
        return machinekit.Jog(instance)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Start',
                'ToolTip'   : 'Start machinekit integration and create objects for each discovered instance'
                }

ToolbarName = 'MachinekitTools'
ToolbarTools = ['MachinekitCommandJog']

def Activated():
    pass

def Deactivated():
    pass

FreeCADGui.addCommand('MachinekitCommandJog', MachinekitCommandJog())
