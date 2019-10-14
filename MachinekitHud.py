import FreeCAD
import FreeCADGui
import MachinekitPreferences
import machinekit
import math

from MKCommand import *
from pivy import coin

class HUD(object):

    def __init__(self, view, coneHeight=5):
        self.view = view
        self.tsze = coneHeight

        self.cam = coin.SoOrthographicCamera()
        self.cam.aspectRatio = 1
        self.cam.viewportMapping = coin.SoCamera.LEAVE_ALONE

        self.pos = coin.SoTranslation()

        self.mat = coin.SoMaterial()
        self.mat.diffuseColor = coin.SbColor(0.9, 0.0, 0.9)
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

        self.tTrf = coin.SoTransform()
        self.tTrf.translation.setValue((0,-self.tsze/2,0))
        self.tTrf.center.setValue((0,self.tsze/2,0))
        self.tTrf.rotation.setValue(coin.SbVec3f((1,0,0)), -math.pi/2)

        self.tPos = coin.SoTranslation()

        self.tMat = coin.SoMaterial()
        self.tMat.diffuseColor = coin.SbColor(0.4, 0.4, 0.4)
        self.tMat.transparency = 0.8

        self.tool = coin.SoCone()
        self.tool.height.setValue(self.tsze)
        self.tool.bottomRadius.setValue(self.tsze/4)

        self.tSep = coin.SoSeparator()
        self.tSep.addChild(self.tPos)
        self.tSep.addChild(self.tTrf)
        self.tSep.addChild(self.tMat)
        self.tSep.addChild(self.tool)

        self.viewer = self.view.getViewer()
        self.render = self.viewer.getSoRenderManager()
        self.sup = None

        self.updatePreferences()
        self.setPosition(0, 0, 0, 0, 0, 0, False, False)

    def updatePreferences(self):
        self.fsze     = MachinekitPreferences.hudFontSize()
        self.fnt.name = MachinekitPreferences.hudFontName()
        self.fnt.size = self.fsze

        size = self.view.getSize()
        ypos = 1 - (2. / size[1]) * self.fsze
        xpos = -0.98 # there's probably a smarter way, but it seems to be OK

        self.pos.translation = (xpos, ypos, 0)

        self.showWorkCoordinates    = MachinekitPreferences.hudShowWorkCoordinates()
        self.showMachineCoordinates = MachinekitPreferences.hudShowMachineCoordinates()

    def axisFmt(self, axis, val, real):
        if self.showWorkCoordinates:
            if self.showMachineCoordinates:
                return "%s: %8.3f %8.3f" % (axis, val, real)
            return "%s: %8.3f" % (axis, val)
        if self.showMachineCoordinates:
            return "%s: %8.3f" % (axis, real)
        return ''

    def setPosition(self, x, X, y, Y, z, Z, homed=True, hot=False):
        if homed:
            self.mat.diffuseColor = coin.SbColor(0.0, 0.9, 0.0)
        else:
            self.mat.diffuseColor = coin.SbColor(0.9, 0.0, 0.9)
        self.txt.string.setValues([self.axisFmt('X', x, X), self.axisFmt('Y', y, Y), self.axisFmt('Z', z, Z)])
        self.tPos.translation = (x, y, z)

        if hot:
            self.tMat.diffuseColor = coin.SbColor(0.9, 0.0, 0.0)
        else:
            self.tMat.diffuseColor = coin.SbColor(0.0, 0.0, 0.9)

    def show(self):
        self.sup = self.render.addSuperimposition(self.sep)
        self.view.getSceneGraph().addChild(self.tSep)
        self.view.getSceneGraph().touch()

    def hide(self):
        if self.sup:
            self.render.removeSuperimposition(self.sup)
            self.sup = None
            self.view.getSceneGraph().removeChild(self.tSep)
            self.view.getSceneGraph().touch()


class Hud(object):
    def __init__(self, mk, view):
        self.mk = mk
        self.hud = HUD(view)
        self.updateUI()
        self.hud.show()
        self.mk.statusUpdate.connect(self.changed)
        self.mk.preferencesUpdate.connect(self.preferencesChanged)

    def terminate(self):
        self.mk.statusUpdate.disconnect(self.changed)
        self.mk = None
        self.hud.hide()

    def displayPos(self, axis):
        actual = self.mk["status.motion.position.actual.%s" % axis]
        offset = self.mk["status.motion.offset.g5x.%s" % axis]
        if actual is None or offset is None:
            return 0, 0
        return actual - offset, actual

    def spindleRunning(self):
        return self.mk['status.motion.spindle.enabled'] and self.mk['status.motion.spindle.speed'] > 0

    def updateUI(self):
        x, X = self.displayPos('x')
        y, Y = self.displayPos('y')
        z, Z = self.displayPos('z')
        hot = self.spindleRunning()
        self.hud.setPosition(x, X, y, Y, z, Z, self.mk.isHomed(), hot)

    def preferencesChanged(self):
        self.hud.updatePreferences()
        self.updateUI()

    def changed(self, service, msg):
        if self.mk:
            self.updateUI()

hud = None

def ToggleHud(mk):
    global hud
    if hud is None:
        hud = Hud(mk, FreeCADGui.ActiveDocument.ActiveView)
    else:
        hud.terminate()
        hud = None
