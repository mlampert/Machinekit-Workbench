# MachinekitCombo combines and manages all MK views.
#
# It creates a tab widget and puts all MK panels into it and also starts the HUD.
# If the Combo is activated again, although it's already open it moves the HUD to
# the currently active 3d view.
#
# This is the panel that is available in the Path workbench (if enabled).

import FreeCAD
import FreeCADGui
import MachinekitExecute
import MachinekitJog
import MachinekitHud
import MachinekitStatus

import machinekit

class Combo(object):
    '''Combination of all MK views for a single MK instance.'''

    def __init__(self, mk):
        self.mk = mk
        self.ui = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('combo.ui'))
        while 0 != self.ui.tabWidget.count():
            self.ui.tabWidget.removeTab(0)

        self.jog = MachinekitJog.Jog(mk)
        self.ui.tabWidget.addTab(self.jog.ui.dockWidgetContents, 'Jog')
        self.exe = MachinekitExecute.Execute(mk)
        self.ui.tabWidget.addTab(self.exe.ui.dockWidgetContents, 'Execute')
        self.status = MachinekitStatus.Status(mk)
        self.ui.tabWidget.addTab(self.status.ui.dockWidgetContents, 'Status')

        self.hud = MachinekitHud.Hud(mk, FreeCADGui.ActiveDocument.ActiveView)
        self.mk.statusUpdate.connect(self.changed)
        self.updateTitle()

    def terminate(self):
        self.mk.statusUpdate.disconnect(self.changed)
        self.mk = None
        self.jog.terminate()
        self.jog = None
        self.exe.terminate()
        self.exe = None
        self.hud.terminate()
        self.hud = None

    def activate(self):
        self.hud.setView(FreeCADGui.ActiveDocument.ActiveView)

    def updateTitle(self):
        if self.mk.isValid():
            self.ui.setWindowTitle(self.mk['status.config.name'])
        else:
            self.ui.setWindowTitle('Machinekit')

    def changed(self, service, msg):
        if self.mk:
            if 'status' in service.topicName():
                self.updateTitle()

