#!/usr/bin/python3

import MKCommand
import MKServicePreview
import MKUtils
import PySide2.QtGui as QtGui
import PySide2.QtCore as QtCore
import PySide2.QtWidgets as QtWidgets
import machinekit
import math
import pivy.coin as coin
import pivy.quarter as quarter
import sys


def previewStraight(preview, points):
    #print('straight', preview.container)
    points.append([preview.container.pos.x, preview.container.pos.y, preview.container.pos.z])

def previewArc(preview, points):
    #print('arc', points[-1], preview.container)
    p0 = points[-1]
    dz = preview.container.pos.z - p0[2]

    x = preview.container.pos.x
    y = preview.container.pos.y
    z = preview.container.pos.z

    cx = preview.container.first_axis
    cy = preview.container.second_axis

    dx = x - cx
    dy = y - cy
    dz = z - p0[2]

    r = math.sqrt(dx * dx + dy * dy)
    steps = int(10 * r) # the bigger the radius the more segments
    a0 = math.atan2(p0[1] - cy, p0[0] - cx)
    a1 = math.atan2(dy, dx)

    #print(steps)
    if preview.container.rotation < 0:
        da = a0 - a1
        while da < 0:
            da += 2 * math.pi
        da = da / steps

        for i in range(steps):
            a = a0 - da * i
            points.append([cx + r * math.cos(a), cy + r * math.sin(a), p0[2] + dz * i])
    else:
        da = a1 - a0
        while da < 0:
            da += 2 * math.pi
        da = da / steps

        for i in range(steps):
            a = a0 + da * i
            points.append([cx + r * math.cos(a), cy + r * math.sin(a), p0[2] + dz * i])

    points.append([preview.container.pos.x, preview.container.pos.y, preview.container.pos.z])

_Preview = {
        MKServicePreview.PreviewStraightTraverse : previewStraight,
        MKServicePreview.PreviewStraightFeed     : previewStraight,
        MKServicePreview.PreviewArcFeed          : previewArc,
        None : None
        }

class PreviewWidget(quarter.QuarterWidget):

    def __init__(self, mk, parent=None):
        quarter.QuarterWidget.__init__(self, parent)
        self.mk = mk

        if mk:
            self.mk.previewUpdate.connect(self.changed)

        img = coin.SoImage()
        img.filename.setValue('Resources/machinekiticon.png')
        root = coin.SoSeparator()
        root.addChild(img)
        self.setSceneGraph(root)

        self.setWindowTitle('Machinekit')

    def changed(self, service, updated):
        points = []
        if service.name == 'preview':
            for preview in service.preview:
                pv = _Preview.get(type(preview), None)
                if pv:
                    pv(preview, points)

            pts = coin.SoCoordinate3()
            pts.point.setValues(0, len(points), points)
            mat = coin.SoMaterial()
            mat.diffuseColor = coin.SbColor((0.7, 0.3, 0.7))
            mat.transparency = 0
            pth = coin.SoLineSet()
            pth.numVertices.setValue(len(points))

            root = coin.SoSeparator()
            root.addChild(mat)
            root.addChild(pts)
            root.addChild(pth)

            self.setSceneGraph(root)


class Machinekit(object):

    def __init__(self):
        self.timer = QtCore.QTimer()
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        self.mk = None
        self.holdoff = 0
        self.preview = None
        self.runPreview = True

        self.preview = PreviewWidget(None)
        self.preview.show()

    def start(self):
        self.timer.start(50)

    def stop(self):
        self.timer.stop()

    def tick(self):
        self.holdoff = self.holdoff - 1
        if machinekit.Instances() or self.holdoff < 1:
            machinekit._update()
        if self.holdoff < 1:
            if self.preview is None and machinekit.Instances():
                self.mk = machinekit.Any()
                self.preview = PreviewWidget(self.mk)
                self.preview.show()
            self.holdoff = 20

        if self.preview and self.runPreview and self.mk and self.mk.isValid():
            if self.mk.gcode:
                print("sending run to preview")
                sequence = MKUtils.taskModeAuto(self.mk)
                sequence.append(MKCommand.MKCommandTaskRun(True))
                self.mk['command'].sendCommands(sequence)
            else:
                print("NOT sending run to preview")
            self.runPreview = False

def main():
    app = QtWidgets.QApplication(sys.argv)

    mk = Machinekit()

    mk.start()
    try:
        rc = app.exec_()
    except KeyboardInterrupt:
        pass
    mk.stop()
    sys.exit(rc)

if __name__ == '__main__':
    main()
