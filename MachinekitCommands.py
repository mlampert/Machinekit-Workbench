# Implementation of all commands the Machinekit workbench registers with FreeCAD.
#
# Special attention should be given to MachinekitCommandCenter. Integrating MK with FC
# turned out to be a bit arkward because the existence and communication with MK is entirely
# outside FC's control, which is not what the FC infrastructure is aiming for.
#
# It is required to monitor all MKs, detect new ones and tear down the ones which went away.
# This requires dynamically modifying menu entries and tool bars.
#
# In order to deal with this situation the MK workbench has a concept of an 'active MK'. Once
# a given MK instance has been set as "active" all tools and menu commands operate against
# that MK instance. This is not ideal there are probably a ton of issues undiscovered so far.
# Note that if only MK instance could be found it becomes automatically the active one.
#
# As it turned out having a separate MK workbench wasn't that useful anyway due to all the
# switching between Path and MK. What I really wanted was for MK to extend Path. Also, this
# idea of having independent views for the different aspects of MK turned out to be less
# useful in practice - which is where the Combo view comes in which is added to the Path
# workbench, one per discovered MK instance, making this much nicer to deal with.

import FreeCAD
import FreeCADGui
import MachinekitCombo
import MachinekitExecute
import MachinekitHud
import MachinekitJog
import MachinekitPreferences
import PathScripts.PathLog as PathLog
import PySide.QtCore
import PySide.QtGui
import machinekit

#PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
#PathLog.trackModule(PathLog.thisModule())

MachinekitUpdateMS  = 50  # update machinekit every 50ms
MachinekitUiHoldoff = 20  # menus and toolbars once a second (20 * 50ms)

MK = None

def _mkerror(mk, msg):
    '''Helper function to display an error in a message box.'''
    mb = PySide.QtGui.QMessageBox()
    mb.setWindowIcon(machinekit.IconResource('machinekiticon.svg'))
    mb.setWindowTitle('Machinekit')
    mb.setTextFormat(PySide.QtCore.Qt.TextFormat.RichText)
    mb.setText("<div align='center'>%s</div>" % '<br/>'.join([mk.name(), ''] + list(msg.messages())))
    if msg.isError():
        mb.setIcon(PySide.QtGui.QMessageBox.Critical)
    elif msg.isText():
        mb.setIcon(PySide.QtGui.QMessageBox.Information)
    else:
        mb.setIcon(PySide.QtGui.QMessageBox.NoIcon)
    mb.setStandardButtons(PySide.QtGui.QMessageBox.Ok)
    mb.exec_()

def SetMK(mk):
    global MK
    if MK:
        MK.errorUpdate.disconnect(_mkerror)
    MK = mk
    mk.errorUpdate.connect(_mkerror)

def ActiveMK(setIfNone=False):
    if MK:
        return MK
    mks = [mk for mk in machinekit.Instances() if mk.isValid()]
    if 1 == len(mks):
        if setIfNone:
            SetMK(mks[0])
        return mks[0]
    return None

class MachinekitCommand(object):
    '''Base class for all Machinekit FC commands.
    Takes care of adding the dock widget and managing its lifetime.'''

    def __init__(self, name, services):
        PathLog.track(services)
        self.name = name
        self.services = services

    def IsActive(self):
        '''MK commands are typically only available if an MK instance is active and there is at least one document open.'''
        return not (ActiveMK() is None or FreeCAD.ActiveDocument is None)

    def Activated(self):
        '''Upon activation create the dock widget, install a signal handler for the close button
        and add the dock widget to FC's mdi.'''
        PathLog.track(self.name)
        dock = None

        if self.haveMK() or ActiveMK(True):
            dock = self.activate(ActiveMK())
        else:
            PathLog.debug('No machinekit instance active')

        if dock:
            PathLog.debug('Activate first found instance')
            for closebutton in [widget for widget in dock.ui.children() if widget.objectName().endswith('closebutton')]:
                closebutton.clicked.connect(lambda : self.terminateDock(dock))
            FreeCADGui.getMainWindow().addDockWidget(PySide.QtCore.Qt.LeftDockWidgetArea, dock.ui)

    def haveMK(self):
        '''Return True if it is not required to have an active machinekit instance for this command'''
        return False

    def serviceNames(self):
        '''Return a list of services required for the command to function.'''
        return self.services

    def terminateDock(self, dock):
        '''Callback invoked when the dock widget's close button is pressed.'''
        PathLog.track()
        dock.terminate()
        FreeCADGui.getMainWindow().removeDockWidget(dock.ui)
        dock.ui.deleteLater()

class MachinekitCommandJog(MachinekitCommand):
    '''FC command to open the Jog dock widget.'''

    def __init__(self):
        PathLog.track()
        super(self.__class__, self).__init__('Jog', ['command', 'status'])

    def activate(self, mk):
        PathLog.track()
        return MachinekitJog.Jog(mk)

    def GetResources(self):
        PathLog.track()
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon-jog.svg'),
                'MenuText'  : 'Jog',
                'ToolTip'   : 'Jog and DRO interface for machine setup'
                }

class MachinekitCommandExecute(MachinekitCommand):
    '''FC command to open the Execute dock widget.'''

    def __init__(self):
        super(self.__class__, self).__init__('Exe', ['command', 'status'])

    def activate(self, mk):
        return MachinekitExecute.Execute(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon-execute.svg'),
                'MenuText'  : 'Execute',
                'ToolTip'   : 'Interface for controlling file execution'
                }

class MachinekitCommandHud(MachinekitCommand):
    '''FC command to add the HUD to the currently active 3d view.'''

    def __init__(self):
        super(self.__class__, self).__init__('Hud', ['command', 'status'])

    def IsActive(self):
        return not (ActiveMK() is None or FreeCADGui.ActiveDocument is None)

    def activate(self, mk):
        MachinekitHud.ToggleHud(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon-hud.svg'),
                'MenuText'  : 'Hud',
                'ToolTip'   : 'HUD DRO interface for machine setup'
                }

class MachinekitCommandCombo(MachinekitCommand):
    '''FC command to start the combo dock in the Path workbench.'''

    def __init__(self, mk=None):
        super(self.__class__, self).__init__('Combo', ['command', 'status'])
        self.combo = {}
        self.mk = mk

    def IsActive(self):
        return (not self.mk is None) or MachinekitCommand.IsActive(self)

    def haveMK(self):
        return not self.mk is None

    def activate(self, mk):
        if self.mk:
            mk = self.mk
        dock = self.combo.get(mk)
        if dock:
            dock.activate()
            return None
        dock = MachinekitCombo.Combo(mk)
        self.combo[mk] = dock
        self.mk.errorUpdate.connect(_mkerror)
        return dock

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.svg'),
                'MenuText'  : 'Combo',
                'ToolTip'   : 'Combo interface with all sub-interfaces'
                }

    def terminateDock(self, dock):
        self.mk.errorUpdate.disconnect(_mkerror)
        del self.combo[dock.mk]
        return MachinekitCommand.terminateDock(self, dock)

class MachinekitCommandPower(MachinekitCommand):
    '''FC menu command to toggle the power of the active MK instance.'''

    def __init__(self, on):
        super(self.__class__, self).__init__('Pwr', ['command', 'status'])
        self.on = on

    def IsActive(self):
        #PathLog.track(self.name)
        return ActiveMK() and ActiveMK().isPowered() != self.on

    def activate(self, mk):
        mk.power()

    def GetResources(self):
        return {
                'MenuText'  : "Power %s" % ('ON' if self.on else 'OFF'),
                'ToolTip'   : 'Turn machinekit controller on/off'
                }

class MachinekitCommandHome(MachinekitCommand):
    '''FC menu command to home all axes.'''

    def __init__(self):
        super(self.__class__, self).__init__('Home', ['command', 'status'])

    def IsActive(self):
        #PathLog.track(self.name)
        return ActiveMK() and ActiveMK().isPowered() and not ActiveMK().isHomed()

    def activate(self, mk):
        mk.home()

    def GetResources(self):
        return {
                'MenuText'  : 'Home',
                'ToolTip'   : 'Home all axes'
                }

class MachinekitCommandActivate(MachinekitCommand):
    '''FC menu command to activate a MK instance.'''

    MenuText = 'Activate'

    def __init__(self):
        super(self.__class__, self).__init__('Activate', None)

    def activate(self, mk):
        SetMK(mk)

    def GetResources(self):
        return {
                'MenuText'  : self.MenuText,
                'ToolTip'   : 'Make Machinekit active'
                }

class MachinekitCommandActivateNone(MachinekitCommand):
    '''FC menu command used when no MK instance can be found.'''

    MenuText = '--no MK found--'

    def __init__(self):
        super(self.__class__, self).__init__('None', None)

    def IsActive(self):
        return False

    def GetResources(self):
        return { 'MenuText'  : self.MenuText }

ToolbarName  = 'MachinekitTools'
ToolbarTools = [MachinekitCommandCombo.__name__, MachinekitCommandHud.__name__, MachinekitCommandJog.__name__, MachinekitCommandExecute.__name__]
MenuName     = 'Machine&kit'
MenuList     = [MachinekitCommandHome.__name__, 'Separator'] + ToolbarTools

class MachinekitCommandCenter(object):
    '''This class orchestrates MK discovery and the associated enabling/disabling of commands.
    If enabled it also adds Combo commands to the Path toolbar.'''

    def __init__(self):
        self.timer = PySide.QtCore.QTimer()
        self.timer.setTimerType(PySide.QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        self.commands = []

        self._addCommand(MachinekitCommandActivate.__name__,       MachinekitCommandActivate())
        self._addCommand(MachinekitCommandActivateNone.__name__,   MachinekitCommandActivateNone())
        self._addCommand(MachinekitCommandPower.__name__ + 'ON',   MachinekitCommandPower(True))
        self._addCommand(MachinekitCommandPower.__name__ + 'OFF',  MachinekitCommandPower(False))
        self._addCommand(MachinekitCommandHome.__name__,           MachinekitCommandHome())
        self._addCommand(MachinekitCommandCombo.__name__,          MachinekitCommandCombo())
        self._addCommand(MachinekitCommandHud.__name__,            MachinekitCommandHud())
        self._addCommand(MachinekitCommandJog.__name__,            MachinekitCommandJog())
        self._addCommand(MachinekitCommandExecute.__name__,        MachinekitCommandExecute())

        self.active = [cmd.IsActive() for cmd in self.commands]
        self.comboTB = {}
        self.comboID = 0
        self.holdoff = 0

    def _addCommand(self, name, cmd):
        self.commands.append(cmd)
        FreeCADGui.addCommand(name, cmd)

    def start(self):
        self.timer.start(MachinekitUpdateMS)

    def stop(self):
        self.timer.stop()

    def isActive(self):
        return self.timer.isActive()

    def tick(self):
        '''Periodically called by the timer to updated menus and tool bars depending on
        discovered and lost MK instances.'''
        self.holdoff = self.holdoff - 1
        if machinekit.Instances() or self.holdoff < 1:
            machinekit._update()
        if self.holdoff < 1:
            active = [cmd.IsActive() for cmd in self.commands]
            def aString(activation):
                return '.'.join(['1' if a else '0' for a in activation])
            if self.active != active:
                PathLog.info("Command activation changed from %s to %s" % (aString(self.active), aString(active)))
                FreeCADGui.updateCommands()
                self.active = active
            self.refreshActivationMenu()
            if MachinekitPreferences.addToPathWB():
                self.refreshComboWB()
            self.holdoff = MachinekitUiHoldoff

    def refreshActivationMenu(self):
        modified = False
        menu = FreeCADGui.getMainWindow().menuBar().findChild(PySide.QtGui.QMenu, MenuName)
        if menu:
            mks = [mk for mk in machinekit.Instances() if mk.isValid()]
            ma = menu.findChild(PySide.QtGui.QMenu, MachinekitCommandActivate.MenuText)
            actions = ma.actions()
            if mks:
                mkNames = [mk.name() for mk in mks]
                for action in actions:
                    name = action.text()
                    if name in mkNames:
                        mkNames.remove(name)
                        mk = [mk for mk in mks if mk.name() == name][0]
                        action.setEnabled(mk != MK)
                    else:
                        modified = True
                        ma.removeAction(action)
                for name in mkNames:
                    mk = [mk for mk in mks if mk.name() == name][0]
                    action = PySide.QtGui.QAction(name, ma)
                    action.setEnabled(mk != MK)
                    PathLog.track(mk.name(), [s for s in mk.instance.endpoint])
                    action.triggered.connect(lambda x=False, mk=mk: self.activate(mk))
                    ma.addAction(action)
                    modified = True
            else:
                if 1 != len(actions) or actions[0].objectName() != MachinekitCommandActivateNone.__name__:
                    for action in actions:
                        ma.removeAction(action)
                    action = PySide.QtGui.QAction(MachinekitCommandActivateNone.MenuText, ma)
                    action.setEnabled(False)
                    ma.addAction(action)
                    modified = True
        return modified

    def refreshComboWB(self):
        if 'PathWorkbench' in FreeCADGui.listWorkbenches():
            wb = FreeCADGui.getWorkbench('PathWorkbench')
            if hasattr(wb, '__Workbench__'):
                MachinekitPreferences.Setup()
                mks = {}
                for mk in [mk for mk in machinekit.Instances() if mk.isValid()]:
                    if self.comboTB.get(mk) is None:
                        name = "%s_%d" % (MachinekitCommandCombo.__name__, self.comboID)
                        cmd = MachinekitCommandCombo(mk)
                        self._addCommand(name, cmd)
                        mks[mk] = (name, cmd)
                        self.comboID = self.comboID + 1
                    else:
                        mks[mk] = self.comboTB[mk]
                tb = FreeCADGui.getMainWindow().findChild(PySide.QtGui.QToolBar, 'MachinekitCombo')
                if tb:
                    # first remove all tool buttons which are no longer valid
                    for mk in [mk for mk in self.comboTB if not mk in mks]:
                        actions = tb.actions()
                        for action in actions:
                            if action.text() == mk.name():
                                PathLog.track('removing', mk.name())
                                tb.removeAction(action)
                    for mk in [mk for mk in mks if not mk in self.comboTB]:
                        icon =  machinekit.IconResource('machinekiticon.svg')
                        PathLog.track('adding', mk.name())
                        tb.addAction(icon, mk.name(), mks[mk][1].Activated)
                elif mks:
                    if 'PathWorkbench' == FreeCADGui.activeWorkbench().name():
                        PathLog.track('createToolbar')
                        tb = PySide.QtGui.QToolBar()
                        tb.setObjectName('MachinekitCombo')
                        for mk in [mk for mk in mks if not mk in self.comboTB]:
                            icon =  machinekit.IconResource('machinekiticon.svg')
                            PathLog.track('adding+', mk.name(), icon)
                            tb.addAction(icon, mk.name(), mks[mk][1].Activated)
                        FreeCADGui.getMainWindow().addToolBar(tb)
                    tools = [mks[mk][0] for mk in mks]
                    PathLog.track('appendToolbar', tools)
                    wb.appendToolbar('MachinekitCombo', tools)
                self.comboTB = mks
            else:
                PathLog.track('no __Workbench__')


    def activate(self, mk):
        PathLog.track(mk)
        SetMK(mk)

_commandCenter = MachinekitCommandCenter()
if MachinekitPreferences.startOnLoad():
    _commandCenter.start()

def Activated():
    PathLog.track()
    if not _commandCenter.isActive():
        _commandCenter.start()

def Deactivated():
    PathLog.track()
    #_commandCenter.stop()


def SetupToolbar(workbench):
    workbench.appendToolbar(ToolbarName, ToolbarTools)

def SetupMenu(workbench):
    workbench.appendMenu([MenuName, 'Activate'], [MachinekitCommandActivateNone.__name__])
    workbench.appendMenu([MenuName, 'Power'], ['MachinekitCommandPowerON', 'MachinekitCommandPowerOFF'])
    workbench.appendMenu([MenuName], MenuList)
