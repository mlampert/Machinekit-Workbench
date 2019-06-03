# Thanks to Chris_G
# https://forum.freecadweb.org/viewtopic.php?f=22&t=16889&start=10#p136770

import FreeCAD as App
import FreeCADGui as Gui
import random

from pivy import coin

fsze = 33

doc = App.newDocument()
view = Gui.ActiveDocument.ActiveView

size = view.getSize()
ypos = 1 - (2 / size[1]) * fsze
xpos = -0.98 # there's probably a smarter way, but it seems to be OK


sep = coin.SoSeparator()

cam = coin.SoOrthographicCamera()
cam.aspectRatio = 1
cam.viewportMapping = coin.SoCamera.LEAVE_ALONE

pos = coin.SoTranslation()
pos.translation = (xpos, ypos, 0)

mat = coin.SoMaterial()
mat.diffuseColor = coin.SbColor(0.9, 0, 0.9)
mat.transparency = 0

fnt = coin.SoFont()
fnt.size = fsze
fnt.name = 'mono'

txt = coin.SoText2()
txt.string = 'setValues'
txt.justification = coin.SoText2.LEFT

sep.addChild(cam)
sep.addChild(pos)
sep.addChild(mat)
sep.addChild(fnt)
sep.addChild(txt)

def randf():
    return random.randint(-1000000, 1000000) / 1000.0

def axisFmt(axis, val):
    return "%s: %8.3f" % (axis, val)

def setValues(x=None, y=None, z=None):
    if x is None:
        x = randf()
    if y is None:
        y = randf()
    if z is None:
        z = randf()

    txt.string.setValues([axisFmt('X', x), axisFmt('Y', y), axisFmt('Z', z)])

setValues()

viewer = view.getViewer()
render = viewer.getSoRenderManager()
sup = render.addSuperimposition(sep)

sg=Gui.ActiveDocument.ActiveView.getSceneGraph()
sg.touch()

##### remove the layer
#render.removeSuperimposition(sup)
#sg.touch()
