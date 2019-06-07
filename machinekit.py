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

        def setupJogButton(b, axes, icon):
            b.clicked.connect(lambda : self.jogAxes(axes))
            b.setIcon(IconResource(icon))
            b.setText('')

        def setupSetButton(b, axes, value, width):
            b.setMaximumWidth(width)
            b.clicked.connect(lambda : self.setAxes(axes, value))

        setupJogButton(self.ui.jogN,  'Y',  'arrow-up.svg')
        setupJogButton(self.ui.jogNE, 'xY', 'arrow-right-up.svg')
        setupJogButton(self.ui.jogE,  'x',  'arrow-right.svg')
        setupJogButton(self.ui.jogSE, 'xy', 'arrow-right-down.svg')
        setupJogButton(self.ui.jogS,  'y',  'arrow-down.svg')
        setupJogButton(self.ui.jogSW, 'Xy', 'arrow-left-down.svg')
        setupJogButton(self.ui.jogW,  'X',  'arrow-left.svg')
        setupJogButton(self.ui.jogNW, 'XY', 'arrow-left-up.svg')
        setupJogButton(self.ui.jog0,  '+',  'home-xy.svg')

        setupJogButton(self.ui.jogU,  'Z',  'arrow-up.svg')
        setupJogButton(self.ui.jogD,  'z',  'arrow-down.svg')
        setupJogButton(self.ui.jogZ0, '-',  'home-z.svg')

        buttonWidth = self.ui.setX.size().height()
        setupSetButton(self.ui.setX,      'x', self.ui.posX.value(), buttonWidth)
        setupSetButton(self.ui.setY,      'y', self.ui.posY.value(), buttonWidth)
        setupSetButton(self.ui.setZ,      'z', self.ui.posZ.value(), buttonWidth)
        setupSetButton(self.ui.setX0,     'x',                    0, buttonWidth)
        setupSetButton(self.ui.setY0,     'y',                    0, buttonWidth)
        setupSetButton(self.ui.setZ0,     'z',                    0, buttonWidth)
        setupSetButton(self.ui.setXYZ0, 'xyz',                    0, buttonWidth)

    def jogAxes(self, axes):
        print('jog:', axes)

    def setAxes(self, axes):
        print('set', axes)

class TreeSelectionObserver(object):
    def __init__(self, notify):
        self.notify = notify
        self.job = None

    def addSelection(self, doc, obj, sub, pnt):
        self.notify()

    def removeSelection(self, doc, obj, sub):
        self.notify()

    def setSelection(self, doc, something=None):
        self.notify()

    def clearSelection(self, doc):
        self.notify()

class Execute(object):
    def __init__(self, mk):
        self.mk = mk
        self.ui = FreeCADGui.PySideUic.loadUi(FileResource('execute.ui'), self)
        self.job = None

        #self.ui.dockWidgetContents.resized.connect(self.resized)

        self.ui.run.clicked.connect(lambda : self.ui.status.setText('run'))
        self.ui.step.clicked.connect(lambda : self.ui.status.setText('step'))
        self.ui.pause.clicked.connect(lambda p: self.ui.status.setText("pause: %s" % p))
        self.ui.stop.clicked.connect(lambda : self.ui.status.setText('stop'))

        self.ui.status.setText('')
        rect = self.ui.geometry()
        self.ui.resize(rect.width(), 0)

        self.observer = TreeSelectionObserver(self.objectSelectionChanged)
        FreeCADGui.Selection.addObserver(self.observer)
        self.objectSelectionChanged()

    def resized(self):
        print('resized')

    def objectSelectionChanged(self):
        jobs = [sel.Object for sel in FreeCADGui.Selection.getSelectionEx() if sel.Object.Name.startswith('Job')]
        if len(jobs) == 1 and jobs[0] != self.job:
            self.job = jobs[0]
        else:
            self.job = None

        if self.job is None:
            self.ui.run.setEnabled(False)
            self.ui.step.setEnabled(False)
        else:
            self.ui.run.setEnabled(True)
            self.ui.step.setEnabled(True)
