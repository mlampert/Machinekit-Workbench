import FreeCAD
import FreeCADGui
import os

from PySide import QtCore, QtGui

def Instances(services):
    return [1]

def PathSource():
    return os.path.dirname(__file__)

def FileResource(filename):
    return "%s/Resources/%s" % (PathSource(), filename)

def IconResource(filename):
    return QtGui.QIcon(FileResource(filename))


class Jog(object):
    def __init__(self, mk):
        self.mk = mk
        self.ui = FreeCADGui.PySideUic.loadUi(FileResource('jog.ui'))

        def setupButton(b, axes, icon):
            b.clicked.connect(lambda : self.jogAxes(axes))
            b.setIcon(IconResource(icon))
            b.setText('')

        setupButton(self.ui.jogN,  'Y',  'arrow-up.svg')
        setupButton(self.ui.jogNE, 'xY', 'arrow-right-up.svg')
        setupButton(self.ui.jogE,  'x',  'arrow-right.svg')
        setupButton(self.ui.jogSE, 'xy', 'arrow-right-down.svg')
        setupButton(self.ui.jogS,  'y',  'arrow-down.svg')
        setupButton(self.ui.jogSW, 'Xy', 'arrow-left-down.svg')
        setupButton(self.ui.jogW,  'X',  'arrow-left.svg')
        setupButton(self.ui.jogNW, 'XY', 'arrow-left-up.svg')
        setupButton(self.ui.jog0,  '+',  'home-xy.svg')

        setupButton(self.ui.jogU,  'Z',  'arrow-up.svg')
        setupButton(self.ui.jogD,  'z',  'arrow-down.svg')
        setupButton(self.ui.jogZ0, '-',  'home-z.svg')

    def jogAxes(self, axes):
        print('jog:', axes)

