# Classes for displaying a HUD terminal in the 3d view.

import FreeCAD
import FreeCADGui
import MachinekitPreferences
import Path
import machinekit
import math

from MKCommand import *
from pivy import coin

class HUD(object):
    '''Class which does the drawing in the 3d view. This is the coin3d dependent implementation.'''

    def __init__(self, view, coneHeight=5):
        self.view = view
        self.tsze = coneHeight

        # DRO
        # Camera used for the DRO to maintain the same size independent of 3d zoom level
        self.cam = coin.SoOrthographicCamera()
        self.cam.aspectRatio = 1
        self.cam.viewportMapping = coin.SoCamera.LEAVE_ALONE

        self.pos = coin.SoTranslation()

        self.mat = coin.SoMaterial()
        self.mat.diffuseColor = coin.SbColor(MachinekitPreferences.hudFontColorUnhomed())
        self.mat.transparency = 0

        self.fnt = coin.SoFont()

        self.txt = coin.SoText2()
        self.txt.string = 'setValues'
        self.txt.justification = coin.SoText2.LEFT

        self.sep = coin.SoSeparator()

        self.sep.addChild(self.cam)
        self.sep.addChild(self.pos)
        self.sep.addChild(self.mat)
        self.sep.addChild(self.fnt)
        self.sep.addChild(self.txt)

        # Tool
        self.tTrf = coin.SoTransform()
        self.tPos = coin.SoTranslation()

        self.tMat = coin.SoMaterial()
        self.tMat.diffuseColor = coin.SbColor(0.4, 0.4, 0.4)
        self.tMat.transparency = 0.8

        self.tSep = coin.SoSeparator()
        self.tSep.addChild(self.tPos)
        self.tSep.addChild(self.tTrf)
        self.tSep.addChild(self.tMat)
        self.tool = None
        self.setToolShape(None)

        self.viewer = self.view.getViewer()
        self.render = self.viewer.getSoRenderManager()
        self.sup = None

        self.updatePreferences()
        self.setPosition(0, 0, 0, 0, 0, 0, False, False)

    def updatePreferences(self):
        '''Callback when preferences have changed to update the visuals accordingly.'''
        self.fsze     = MachinekitPreferences.hudFontSize()
        self.fnt.name = MachinekitPreferences.hudFontName()
        self.fnt.size = self.fsze

        self.mat.diffuseColor = coin.SbColor(MachinekitPreferences.hudFontColorUnhomed())

        size = self.view.getSize()
        ypos = 1 - (2. / size[1]) * self.fsze
        xpos = -0.98 # there's probably a smarter way, but it seems to be OK

        self.pos.translation = (xpos, ypos, 0)

        self.showWorkCoordinates    = MachinekitPreferences.hudShowWorkCoordinates()
        self.showMachineCoordinates = MachinekitPreferences.hudShowMachineCoordinates()

    def axisFmt(self, axis, val, real):
        '''Returns the formatted string for the given axis for the DRO.'''
        if self.showWorkCoordinates:
            if self.showMachineCoordinates:
                return "%s: %8.3f %8.3f" % (axis, val, real)
            return "%s: %8.3f" % (axis, val)
        if self.showMachineCoordinates:
            return "%s: %8.3f" % (axis, real)
        return ''

    def setPosition(self, x, X, y, Y, z, Z, homed=True, spinning=False):
        '''Update the DRO and the tool position according to the given values.'''
        if homed:
            self.mat.diffuseColor = coin.SbColor(MachinekitPreferences.hudFontColorHomed())
        else:
            self.mat.diffuseColor = coin.SbColor(MachinekitPreferences.hudFontColorUnhomed())
        self.txt.string.setValues([self.axisFmt('X', x, X), self.axisFmt('Y', y, Y), self.axisFmt('Z', z, Z)])
        self.tPos.translation = (x, y, z)

        if spinning:
            self.tMat.diffuseColor = coin.SbColor(MachinekitPreferences.hudToolColorSpinning())
        else:
            self.tMat.diffuseColor = coin.SbColor(MachinekitPreferences.hudToolColorStopped())

    def setToolShape(self, shape):
        '''Takes the actual shape of the tool and copies it into the 3d view.
        Should the tool in question be a legacy tool without a shape the tool
        is stylized by the traditional inverted cone.'''
        if self.tool:
            self.tSep.removeChild(self.tool)
        if shape and MachinekitPreferences.hudToolShowShape():
            buf = shape.writeInventor()
            cin = coin.SoInput()
            cin.setBuffer(buf)
            self.tool = coin.SoDB.readAll(cin)
            # the shape is correct, but we need to adjust the offset
            self.tTrf.translation.setValue((0, 0, -shape.BoundBox.ZMin))
            self.tTrf.center.setValue((0,0,0))
            self.tTrf.rotation.setValue(coin.SbVec3f((0,0,0)), 0)
        else:
            self.tool = coin.SoCone()
            self.tool.height.setValue(self.tsze)
            self.tool.bottomRadius.setValue(self.tsze/4)
            # we need to flip and translate the cone so it sits on it's top
            self.tTrf.translation.setValue((0, -self.tsze/2, 0))
            self.tTrf.center.setValue((0, self.tsze/2, 0))
            self.tTrf.rotation.setValue(coin.SbVec3f((1,0,0)), -math.pi/2)
        self.tSep.addChild(self.tool)

    def show(self):
        '''Make HUD visible in 3d view.'''
        self.sup = self.render.addSuperimposition(self.sep)
        self.view.getSceneGraph().addChild(self.tSep)
        self.view.getSceneGraph().touch()

    def hide(self):
        '''Hide HUD from 3d view.'''
        if self.sup:
            self.render.removeSuperimposition(self.sup)
            self.sup = None
            self.view.getSceneGraph().removeChild(self.tSep)
            self.view.getSceneGraph().touch()


class Hud(object):
    '''Coordinator class to manage a visual HUD and integrate it with the MK status updates
    and FC's framework.'''

    def __init__(self, mk, view):
        self.mk = mk
        self.tool = 0
        self.hud = None
        self.setView(view)
        self.mk.statusUpdate.connect(self.changed)
        self.mk.preferencesUpdate.connect(self.preferencesChanged)

    def setView(self, view):
        '''setView(vieww) ... used to set the 3d view where to make the HUD visible.
        If the HUD is already visible on a different view it is removed from there.'''
        if self.hud and self.hud.view != view:
            self.hud.hide()
            self.hud = None
        if not self.hud:
            self.hud = HUD(view)
            self.updateUI()
            self.hud.show()

    def terminate(self):
        '''Hide the HUD and take all structures down.'''
        self.mk.statusUpdate.disconnect(self.changed)
        self.mk = None
        self.hud.hide()

    def displayPos(self, axis):
        '''displayPos(axis) ... returns the position of the given axis that should get displayed.'''
        actual = self.mk["status.motion.position.actual.%s" % axis]
        offset = self.mk["status.motion.offset.g5x.%s" % axis]
        if actual is None or offset is None:
            return 0, 0
        return actual - offset, actual

    def spindleRunning(self):
        '''Return True if the spindle is currently rotating.'''
        return self.mk['status.motion.spindle.enabled'] and self.mk['status.motion.spindle.speed'] > 0

    def updateUI(self):
        '''Callback invoked when something changed, will refresh the 3d view accordingly.'''
        x, X = self.displayPos('x')
        y, Y = self.displayPos('y')
        z, Z = self.displayPos('z')
        spinning = self.spindleRunning()
        tool = self.mk['status.io.tool.nr']
        if tool is None:
            tool = 0
        if tool != self.tool:
            shape = None
            if tool != 0 and self.mk and self.mk.getJob():
                job = self.mk.getJob()
                for tc in job.ToolController:
                    if tc.ToolNumber == tool:
                        t = tc.Tool
                        if not isinstance(t, Path.Tool) and hasattr(t, 'Shape'):
                            shape = t.Shape
                        else:
                            print("%s does not have a shape" % t)
                        break
            self.hud.setToolShape(shape)
            self.tool = tool
        self.hud.setPosition(x, X, y, Y, z, Z, self.mk.isHomed(), spinning)

    def preferencesChanged(self):
        '''Callback invoked when the Machinekit workbench preferences changed. Updates the view accoringly.'''
        self.hud.updatePreferences()
        if self.mk:
            self.updateUI()

    def changed(self, service, msg):
        '''Callback invoked when MK sends a status update.'''
        if self.mk:
            self.updateUI()

hud = None

def ToggleHud(mk, forceOn=False):
    global hud
    if hud is None or forceOn:
        hud = Hud(mk, FreeCADGui.ActiveDocument.ActiveView)
    else:
        hud.terminate()
        hud = None
    return hud

