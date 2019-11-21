# Classes for displaying a HUD terminal in the 3d view.

import FreeCAD
import FreeCADGui
import MachinekitPreferences
import Path
import PathLength
import machinekit
import machinetalk.protobuf.status_pb2 as STATUS
import math
import time

from MKCommand import *
from pivy import coin

class Coin3DNode(object):

    def updatePreferences(self):
        pass
    def updateJob(self, mk):
        pass
    def setPosition(self, x, X, y, Y, z, Z, homed, spinning, mk):
        pass
    def updateUI(self, mk):
        pass

class DRO(Coin3DNode):
    '''Class displaying the DRO in the HUD.'''

    def __init__(self, view):
        self.view = view

        self.pos = coin.SoTranslation()

        self.mat = coin.SoMaterial()
        self.mat.diffuseColor = coin.SbColor(MachinekitPreferences.hudFontColorUnhomed())
        self.mat.transparency = 0

        self.fnt = coin.SoFont()

        self.txt = coin.SoText2()
        self.txt.string = 'setValues'
        self.txt.justification = coin.SoText2.LEFT

        self.sep = coin.SoSeparator()

        self.sep.addChild(self.pos)
        self.sep.addChild(self.mat)
        self.sep.addChild(self.fnt)
        self.sep.addChild(self.txt)

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

    def setPosition(self, x, X, y, Y, z, Z, homed, spinning, mk):
        '''Update the DRO according to the given values.'''
        if homed:
            self.mat.diffuseColor = coin.SbColor(MachinekitPreferences.hudFontColorHomed())
        else:
            self.mat.diffuseColor = coin.SbColor(MachinekitPreferences.hudFontColorUnhomed())
        self.txt.string.setValues([self.axisFmt('X', x, X), self.axisFmt('Y', y, Y), self.axisFmt('Z', z, Z)])

class TaskProgress(Coin3DNode):
    '''Class displaying the DRO in the HUD.'''

    MinX = -0.98
    MinY = -0.95
    MaxX = +0.90
    MaxY = -0.90

    Color = MachinekitPreferences._unsigned2fractions(0xff0657ad)

    def __init__(self, view):
        self.view = view

        # Background
        self.posB = coin.SoTranslation()
        self.matB = self._material(0.8)
        self.cooB = coin.SoCoordinate3()
        self.fceB = coin.SoFaceSet()

        self.cooB.point.setValues(self.pointsScaledTo(1))

        self.sepB = coin.SoSeparator()

        self.sepB.addChild(self.posB)
        self.sepB.addChild(self.matB)
        self.sepB.addChild(self.cooB)
        self.sepB.addChild(self.fceB)

        # Foreground
        self.posF = coin.SoTranslation()
        self.matF = self._material(0.7)
        self.cooF = coin.SoCoordinate3()
        self.fceF = coin.SoFaceSet()

        self.sepF = coin.SoSeparator()

        self.sepF.addChild(self.posF)
        self.sepF.addChild(self.matF)
        self.sepF.addChild(self.cooF)
        self.sepF.addChild(self.fceF)

        self.prgr = coin.SoSwitch()
        self.prgr.addChild(self.sepF)
        self.prgr.whichChild = coin.SO_SWITCH_NONE

        # Runtime
        self.posR = coin.SoTranslation()
        self.matR = self._material(0)
        self.fntR = coin.SoFont()
        self.txtR = coin.SoText2()

        self.posR.translation = (self.MinX, self.MinY, 0)

        fntSize = int(self.view.getSize()[1] * float(self.MaxY - self.MinY))

        self.fntR.name = MachinekitPreferences.hudFontName()
        self.fntR.size = fntSize

        self.txtR.string = '0s'
        self.txtR.justification = coin.SoText2.LEFT

        self.sepR = coin.SoSeparator()
        self.sepR.addChild(self.posR)
        self.sepR.addChild(self.matR)
        self.sepR.addChild(self.fntR)
        self.sepR.addChild(self.txtR)

        # Total time
        self.posT = coin.SoTranslation()
        self.matT = self._material(0)
        self.fntT = coin.SoFont()
        self.txtT = coin.SoText2()

        self.posT.translation = (self.MaxX, self.MinY, 0)
        self.fntT.name = MachinekitPreferences.hudFontName()
        self.fntT.size = fntSize
        self.txtT.string = '0s'
        self.txtT.justification = coin.SoText2.RIGHT

        self.sepT = coin.SoSeparator()
        self.sepT.addChild(self.posT)
        self.sepT.addChild(self.matT)
        self.sepT.addChild(self.fntT)
        self.sepT.addChild(self.txtT)

        # tie everything together under a switch
        self.sep = coin.SoSwitch()
        self.sep.addChild(self.sepB)
        self.sep.addChild(self.prgr)
        self.sep.addChild(self.sepR)
        self.sep.addChild(self.sepT)
        self.sep.whichChild = coin.SO_SWITCH_NONE

        # timing
        self.start = None
        self.elapsed = None
        self.line = None
        self.pathLength = None

    def _material(self, transparency):
        mat = coin.SoMaterial()
        mat.diffuseColor = coin.SbColor(self.Color)
        mat.transparency = transparency
        return mat

    def _formatTime(self, dt):
        m = int(dt / 60)
        s = int(dt % 60)
        return "%2d:%02d" % (m, s)

    def pointsScaledTo(self, factor):
        # points need to be counter clockwise for the face to look up (and have a color)
        x = factor * (self.MaxX - self.MinX) + self.MinX
        p0 = (self.MinX, self.MaxY, 0)
        p1 = (self.MinX, self.MinY, 0)
        p2 = (x,         self.MinY, 0)
        p3 = (x,         self.MaxY, 0)
        return [p0, p1, p2, p3]

    def setPosition(self, x, X, y, Y, z, Z, homed, spinning, mk):
        if not (mk is None or mk['status.motion.line'] is None or mk['status.task'] is None or mk['status.task.task.mode'] != STATUS.EMC_TASK_MODE_AUTO):
            self.sep.whichChild = coin.SO_SWITCH_ALL
            if mk['status.motion.line'] > 0:
                if self.start is None:
                    self.start = time.monotonic()
                    self.pathLength = PathLength.FromGCode(mk.gcode)
                currentLine = mk['status.motion.line']
                done = self.pathLength.percentDone(currentLine, mk['status.motion.distance_left'])
                self.cooF.point.setValues(self.pointsScaledTo(done))
                elapsed = time.monotonic() - self.start
                self.txtR.string = self._formatTime(elapsed)
                if self.elapsed != int(elapsed): # and self.line != currentLine:
                    estimated = elapsed / done
                    self.txtT.string = self._formatTime(estimated)
                    self.elapsed = int(elapsed)
                    self.line = currentLine
                self.prgr.whichChild = coin.SO_SWITCH_ALL
            else:
                self.start = None
                self.elapsed = None
                self.line = None
                self.prgr.whichChild = coin.SO_SWITCH_NONE
        else:
            self.start = None
            self.elapsed = None
            self.line = None
            self.sep.whichChild = coin.SO_SWITCH_NONE


class Tool(Coin3DNode):
    '''Class to display the tool in the 3d view.'''

    def __init__(self, view, coneHeight):
        self.view = view
        self.tsze = coneHeight

        self.trf = coin.SoTransform()
        self.pos = coin.SoTranslation()

        self.mat = coin.SoMaterial()
        self.mat.diffuseColor = coin.SbColor(0.4, 0.4, 0.4)
        self.mat.transparency = 0.8

        self.sep = coin.SoSeparator()
        self.sep.addChild(self.pos)
        self.sep.addChild(self.trf)
        self.sep.addChild(self.mat)
        self.tool = None
        self.setToolShape(None)

    def setPosition(self, x, X, y, Y, z, Z, homed, spinning, mk):
        '''Update the tool position according to the given values.'''
        self.pos.translation = (x, y, z)

        if spinning:
            self.mat.diffuseColor = coin.SbColor(MachinekitPreferences.hudToolColorSpinning())
        else:
            self.mat.diffuseColor = coin.SbColor(MachinekitPreferences.hudToolColorStopped())

    def setToolShape(self, shape):
        '''Takes the actual shape of the tool and copies it into the 3d view.
        Should the tool in question be a legacy tool without a shape the tool
        is stylized by the traditional inverted cone.'''
        if self.tool:
            self.sep.removeChild(self.tool)
        if shape and MachinekitPreferences.hudToolShowShape():
            buf = shape.writeInventor()
            cin = coin.SoInput()
            cin.setBuffer(buf)
            self.tool = coin.SoDB.readAll(cin)
            # the shape is correct, but we need to adjust the offset
            self.trf.translation.setValue((0, 0, -shape.BoundBox.ZMin))
            self.trf.center.setValue((0,0,0))
            self.trf.rotation.setValue(coin.SbVec3f((0,0,0)), 0)
        else:
            self.tool = coin.SoCone()
            self.tool.height.setValue(self.tsze)
            self.tool.bottomRadius.setValue(self.tsze/4)
            # we need to flip and translate the cone so it sits on it's top
            self.trf.translation.setValue((0, -self.tsze/2, 0))
            self.trf.center.setValue((0, self.tsze/2, 0))
            self.trf.rotation.setValue(coin.SbVec3f((1,0,0)), -math.pi/2)
        self.sep.addChild(self.tool)

class HUD(object):
    '''Class which does the drawing in the 3d view. This is the coin3d dependent implementation.'''

    def __init__(self, view, coneHeight=5):
        self.view = view

        self.dro = DRO(view)
        self.tsk = TaskProgress(view)

        # Camera used for the DRO to maintain the same size independent of 3d zoom level
        self.cam = coin.SoOrthographicCamera()
        self.cam.aspectRatio = 1
        self.cam.viewportMapping = coin.SoCamera.LEAVE_ALONE

        # Here's the thing, there is no need for a light in order to display text. But for
        # the faces a light is required otherwise they'll always be black - and one can spend
        # hours to try and make them a different color.
        self.lgt = coin.SoDirectionalLight()

        self.sep = coin.SoSeparator()
        self.sep.addChild(self.cam)
        self.sep.addChild(self.lgt)
        self.sep.addChild(self.dro.sep)
        self.sep.addChild(self.tsk.sep)

        self.tool = Tool(view, coneHeight)

        self.viewer = self.view.getViewer()
        self.render = self.viewer.getSoRenderManager()
        self.sup = None

        self.updatePreferences()
        self.setPosition(0, 0, 0, 0, 0, 0, False, False, None)

    def updatePreferences(self):
        '''Callback when preferences have changed to update the visuals accordingly.'''
        self.dro.updatePreferences()
        self.tsk.updatePreferences()
        self.tool.updatePreferences()

    def updateJob(self, mk):
        self.dro.updateJob(mk)
        self.tsk.updateJob(mk)
        self.tool.updateJob(mk)

    def setPosition(self, x, X, y, Y, z, Z, homed, spinning, mk):
        '''Update the DRO and the tool position according to the given values.'''
        self.dro.setPosition(x, X, y, Y, z, Z, homed, spinning, mk)
        self.tsk.setPosition(x, X, y, Y, z, Z, homed, spinning, mk)
        self.tool.setPosition(x, X, y, Y, z, Z, homed, spinning, mk)

    def setToolShape(self, shape):
        '''Update the shape of the tool'''
        self.tool.setToolShape(shape)

    def show(self):
        '''Make HUD visible in 3d view.'''
        self.sup = self.render.addSuperimposition(self.sep)
        self.view.getSceneGraph().addChild(self.tool.sep)
        self.view.getSceneGraph().touch()

    def hide(self):
        '''Hide HUD from 3d view.'''
        if self.sup:
            self.render.removeSuperimposition(self.sup)
            self.sup = None
            self.view.getSceneGraph().removeChild(self.tool.sep)
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
        self.mk.jobUpdate.connect(self.jobChanged)

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
        self.hud.setPosition(x, X, y, Y, z, Z, self.mk.isHomed(), spinning, self.mk)

    def preferencesChanged(self):
        '''Callback invoked when the Machinekit workbench preferences changed. Updates the view accoringly.'''
        self.hud.updatePreferences()
        if self.mk:
            self.updateUI()

    def jobChanged(self, job):
        self.hud.updateJob(self.mk)

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

