import FreeCAD
import FreeCADGui
import MachinekitExecute
import MachinekitHud
import MachinekitJog
import PathScripts.PathLog as PathLog
import PySide.QtCore
import PySide.QtGui
import machinekit

#PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())
#PathLog.trackModule(PathLog.thisModule())

def _mkerror(service, msg):
    mb = PySide.QtGui.QMessageBox()
    mb.setWindowIcon(machinekit.IconResource('machinekiticon.png'))
    mb.setWindowTitle('Machinekit')
    mb.setTextFormat(PySide.QtCore.Qt.TextFormat.RichText)
    mb.setText("<div align='center'>%s</div>" % '<br/>'.join(msg.messages()))
    if msg.isError():
        mb.setIcon(PySide.QtGui.QMessageBox.Critical)
    elif msg.isText():
        mb.setIcon(PySide.QtGui.QMessageBox.Information)
    else:
        mb.setIcon(PySide.QtGui.QMessageBox.NoIcon)
    mb.setStandardButtons(PySide.QtGui.QMessageBox.Ok)
    mb.exec_()

MK = None

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
    def __init__(self, name, services):
        PathLog.track(services)
        self.name = name
        self.services = services

    def IsActive(self):
        #PathLog.track(self.name)
        return not ActiveMK() is None

    def Activated(self):
        PathLog.track(self.name)
        dock = None

        if ActiveMK(True):
            dock = self.activate(ActiveMK())
        else:
            PathLog.debug('No machinekit instance active')

        if dock is None:
            PathLog.debug('No dock to activate')
        else:
            PathLog.debug('Activate first found instance')
            for closebutton in [widget for widget in dock.ui.children() if widget.objectName().endswith('closebutton')]:
                closebutton.clicked.connect(lambda : self.terminateDock(dock))
            FreeCADGui.getMainWindow().addDockWidget(PySide.QtCore.Qt.LeftDockWidgetArea, dock.ui)

    def serviceNames(self):
        return self.services

    def terminateDock(self, dock):
        PathLog.track()
        dock.terminate()
        FreeCADGui.getMainWindow().removeDockWidget(dock.ui)
        dock.ui.deleteLater()

class MachinekitCommandJog(MachinekitCommand):
    def __init__(self):
        PathLog.track()
        super(self.__class__, self).__init__('Jog', ['command', 'status'])

    def activate(self, mk):
        PathLog.track()
        return MachinekitJog.Jog(mk)

    def GetResources(self):
        PathLog.track()
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Jog',
                'ToolTip'   : 'Jog and DRO interface for machine setup'
                }

class MachinekitCommandExecute(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__('Exe', ['command', 'status'])

    def activate(self, mk):
        return MachinekitExecute.Execute(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Execute',
                'ToolTip'   : 'Interface for controlling file execution'
                }

class MachinekitCommandHud(MachinekitCommand):
    def __init__(self):
        super(self.__class__, self).__init__('Hud', ['command', 'status'])

    def IsActive(self):
        #PathLog.track(self.name)
        return not (ActiveMK() is None or FreeCADGui.ActiveDocument is None)

    def activate(self, mk):
        MachinekitHud.ToggleHud(mk)

    def GetResources(self):
        return {
                'Pixmap'    : machinekit.FileResource('machinekiticon.png'),
                'MenuText'  : 'Hud',
                'ToolTip'   : 'HUD DRO interface for machine setup'
                }


class MachinekitCommandPower(MachinekitCommand):
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
    MenuText = '--no MK found--'

    def __init__(self):
        super(self.__class__, self).__init__('None', None)

    def IsActive(self):
        return False

    def GetResources(self):
        return { 'MenuText'  : self.MenuText }

ToolbarName  = 'MachinekitTools'
ToolbarTools = [MachinekitCommandHud.__name__, MachinekitCommandJog.__name__, MachinekitCommandExecute.__name__]
MenuName     = 'Machine&kit'
MenuList     = [MachinekitCommandHome.__name__, 'Separator'] + ToolbarTools

class MachinekitCommandCenter(object):
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
        self._addCommand(MachinekitCommandHud.__name__,            MachinekitCommandHud())
        self._addCommand(MachinekitCommandJog.__name__,            MachinekitCommandJog())
        self._addCommand(MachinekitCommandExecute.__name__,        MachinekitCommandExecute())

        self.active = [cmd.IsActive() for cmd in self.commands]

    def _addCommand(self, name, cmd):
        self.commands.append(cmd)
        FreeCADGui.addCommand(name, cmd)

    def start(self):
        self.timer.start(50)

    def stop(self):
        self.timer.stop()

    def tick(self):
        machinekit._update()
        active = [cmd.IsActive() for cmd in self.commands]
        def aString(activation):
            return '.'.join(['1' if a else '0' for a in activation])
        if self.active != active:
            PathLog.info("Command activation changed from %s to %s" % (aString(self.active), aString(active)))
            FreeCADGui.updateCommands()
            self.active = active
        self.refreshActivationMenu()

    def refreshActivationMenu(self):
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
                        ma.removeAction(action)
                for name in mkNames:
                    mk = [mk for mk in mks if mk.name() == name][0]
                    action = PySide.QtGui.QAction(name, ma)
                    action.setEnabled(mk != MK)
                    PathLog.track(mk.name(), [s for s in mk.instance.endpoint])
                    action.triggered.connect(lambda x=False, mk=mk: self.activate(mk))
                    ma.addAction(action)
            else:
                if 1 != len(actions) or actions[0].objectName() != MachinekitCommandActivateNone.__name__:
                    for action in actions:
                        ma.removeAction(action)
                    action = PySide.QtGui.QAction(MachinekitCommandActivateNone.MenuText, ma)
                    action.setEnabled(False)
                    ma.addAction(action)

    def activate(self, mk):
        PathLog.track(mk)
        SetMK(mk)

_commandCenter = MachinekitCommandCenter()

def Activated():
    PathLog.track()
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
