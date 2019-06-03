import FreeCAD
import FreeCADGui
import machinekit

class MachinekitStartCmd(object):
    def Activated(self, index):
        if index == 0:
            machinekit.Start()
        else:
            machinekit.Stop()

    def GetResources(self):
        return {
                'Pixmap'    : FreeCAD.getHomePath() + "Mod/Machinekit/Resources/machinekiticon.png",
                'MenuText'  : 'Start',
                'ToolTip'   : 'Start machinekit integration and create objects for each discovered instance',
                'Checkable' : True}

FreeCADGui.addCommand('MachinekitStartCmd', MachinekitStartCmd())
