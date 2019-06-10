import FreeCAD
import FreeCADGui
import machinekit
import math

from MKCommand import *
from pivy import coin

def axisFmt(axis, val):
    return "%s: %8.3f" % (axis, val)

class HUD(object):
    def __init__(self, view, fontSize=33, coneHeight=30):
        self.view = view
        self.fsze = fontSize
        self.tsze = coneHeight

        size = view.getSize()
        ypos = 1 - (2 / size[1]) * self.fsze
        xpos = -0.98 # there's probably a smarter way, but it seems to be OK

        self.cam = coin.SoOrthographicCamera()
        self.cam.aspectRatio = 1
        self.cam.viewportMapping = coin.SoCamera.LEAVE_ALONE

        self.pos = coin.SoTranslation()
        self.pos.translation = (xpos, ypos, 0)

        self.mat = coin.SoMaterial()
        self.mat.diffuseColor = coin.SbColor(0.9, 0, 0.9)
        self.mat.transparency = 0

        self.fnt = coin.SoFont()
        self.fnt.size = self.fsze
        self.fnt.name = 'mono'

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
        self.tPos.translation = (xpos, ypos, 0)

        self.tMat = coin.SoMaterial()
        self.tMat.diffuseColor = coin.SbColor(0.9, 0, 0.9)
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

        self.up = 0
        self.setPosition(0, 0, 0)

    def setPosition(self, x, y, z):
        print(self.up)
        self.up += 1
        self.txt.string.setValues([axisFmt('X', x), axisFmt('Y', y), axisFmt('Z', z)])
        self.tPos.translation = (x, y, z)

        self.sep.touch()
        self.tSep.touch()

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
        self.status = self.mk.connectWith('status')
        self.status.attach(self)
        self.updateUI()
        self.hud.show()

    def terminate(self):
        self.status.detach(self)
        self.hud.hide()

    def displayPos(self, axis):
        return self.status["motion.position.actual.%s" % axis] - self.status["motion.offset.g5x.%s" % axis]

    def updateUI(self):
        x = self.displayPos('x')
        y = self.displayPos('y')
        z = self.displayPos('z')
        self.hud.setPosition(x, y, z)

    def changed(self, service, msg):
        self.updateUI()

hud = None

def ToggleHud(mk):
    global hud
    if hud is None:
        hud = Hud(mk, FreeCADGui.ActiveDocument.ActiveView)
    else:
        hud.terminate()
        hud = None
