# Classes and functions to deal with the Machinkit workbench's preferences

import FreeCAD
import json

PreferenceStartOnLoad = 'GeneralStartOnLoad'
PreferenceAddToPathWB = 'GeneralAddToPathWB'
PreferenceRestServers = 'GeneralRestServer'

PreferenceHudWorkCoordinates = "HudWorkCoordinates"
PreferenceHudMachineCoordinates = "HudMachineCoordinates"

PreferenceHudFontName  = "HudFontName"
PreferenceHudFontSize  = "HudFontSize"
PreferenceHudFontColorUnhomed = "HudFontColorUnhomed"
PreferenceHudFontColorHomed   = "HudFontColorHomed"

PreferenceHudToolShowShape     = "HudToolShowShape"
PreferenceHudToolColorStopped  = "HudToolColorStopped"
PreferenceHudToolColorSpinning = "HudToolColorSpinning"

PreferenceHudProgrHide      = "HudProgrHide"
PreferenceHudProgrBar       = "HudProgrBar"
PreferenceHudProgrPercent   = "HudProgrPercent"
PreferenceHudProgrElapsed   = "HudProgrElapsed"
PreferenceHudProgrRemaining = "HudProgrRemaining"
PreferenceHudProgrTotal     = "HudProgrTotal"
PreferenceHudProgrFontName  = "HudProgrFontName"
PreferenceHudProgrFontSize  = "HudProgrFontSize"
PreferenceHudProgrColor     = "HudProgrColor"

def preferences():
    '''Return the FC MK workbench preferences.'''
    return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Machinekit")

def startOnLoad():
    '''Return True if 'start on load' is enabled (the default).'''
    return preferences().GetBool(PreferenceStartOnLoad, True)

def addToPathWB():
    '''Return True if MK Combo commands should be added to the Path workbench toolbar (the default).'''
    return preferences().GetBool(PreferenceAddToPathWB, True)

def restServers():
    '''Return a list of host:port to check for service announcements.'''
    return json.loads(preferences().GetString(PreferenceRestServers, '{}'))

def setGeneralPreferences(start, pathWB, restSrvs):
    '''API to set the general preferences.'''
    pref = preferences()
    pref.SetBool(PreferenceStartOnLoad, start)
    pref.SetBool(PreferenceAddToPathWB, pathWB)
    pref.SetString(PreferenceRestServers, json.dumps(restSrvs))

def hudFontName():
    '''Return the configured font name to be used for the HUD (default is mono).'''
    return preferences().GetString(PreferenceHudFontName, 'mono')

def hudFontSize():
    '''Return the configured font size to be used for the HUD (default is 33).'''
    return preferences().GetInt(PreferenceHudFontSize, 33)

def _unsigned2fractions(u):
    def frac(i, b):
        return ((i >> (8 * b)) & 0xFF) / 255.0
    return (frac(u, 2), frac(u, 1), frac(u, 0))

def _color(name, default, raw):
    color = preferences().GetUnsigned(name, default)
    if raw:
        return color
    return _unsigned2fractions(color)

def hudFontColorUnhomed(raw=False):
    '''Return the configured HUD font color to be used when the tool is not homed.'''
    return _color(PreferenceHudFontColorUnhomed, 0xffaa00aa, raw)

def hudFontColorHomed(raw=False):
    '''Return the configured HUD font color to be used when the tool IS homed.'''
    return _color(PreferenceHudFontColorHomed, 0xff007400, raw)

def hudShowWorkCoordinates():
    '''Retrn True if the work coordinates should be displayed in the HUD.'''
    return preferences().GetBool(PreferenceHudWorkCoordinates, True)

def hudShowMachineCoordinates():
    '''Retrn True if the machine coordinates should be displayed in the HUD.'''
    return preferences().GetBool(PreferenceHudMachineCoordinates, False)

def hudToolShowShape():
    '''Retrn True if the tool should be displayed by its actual shape, otherwise it'll be stylised by an inverted cone.'''
    return preferences().GetBool(PreferenceHudToolShowShape, True)

def hudToolColorStopped(raw=False):
    '''Return color to be used for the tool if the spindle is not rotating.'''
    return _color(PreferenceHudToolColorStopped, 0xff0000e5, raw)

def hudToolColorSpinning(raw=False):
    '''Return color to be used for the tool if the spindle IS rotating.'''
    return _color(PreferenceHudToolColorSpinning, 0xffe50000, raw)

def hudProgrHide():
    '''Return True if progress is hidden if task is inactive.'''
    return preferences().GetBool(PreferenceHudProgrHide, True)

def hudProgrBar():
    '''Return True if progress bar is displayed.'''
    return preferences().GetBool(PreferenceHudProgrBar, True)

def hudProgrElapsed():
    '''Return True if the elapsed time of task execution is displayed.'''
    return preferences().GetBool(PreferenceHudProgrElapsed, True)

def hudProgrRemaining():
    '''Return True if the remaining time of task execution is displayed.'''
    return preferences().GetBool(PreferenceHudProgrRemaining, False)

def hudProgrTotal():
    '''Return True if the total time of task execution is displayed.'''
    return preferences().GetBool(PreferenceHudProgrTotal, True)

def hudProgrPercent():
    '''Return True if the percent of task execution completion is displayed.'''
    return preferences().GetBool(PreferenceHudProgrPercent, False)

def hudProgrFontName():
    '''Return the progress font name'''
    return preferences().GetString(PreferenceHudProgrFontName, 'mono')

def hudProgrFontSize():
    '''Return the progress font size'''
    return preferences().GetInt(PreferenceHudProgrFontSize, 30)

def hudProgrColor(raw=False):
    '''Return the color for the task progress display.'''
    return _color(PreferenceHudProgrColor, 0xff0657ad, raw)

def setHudPreferences(workCoordinates, machineCoordinates):
    '''Set HUD coordinate display preferences.'''
    pref = preferences()
    pref.SetBool(PreferenceHudWorkCoordinates, workCoordinates)
    pref.SetBool(PreferenceHudMachineCoordinates, machineCoordinates)

def setHudPreferencesFont(fontName, fontSize, fontColorUnhomed, fontColorHomed):
    '''Set HUD font preferences.'''
    pref = preferences()
    pref.SetInt(PreferenceHudFontSize, fontSize)
    pref.SetString(PreferenceHudFontName, fontName)
    pref.SetUnsigned(PreferenceHudFontColorUnhomed, fontColorUnhomed.rgba())
    pref.SetUnsigned(PreferenceHudFontColorHomed, fontColorHomed.rgba())

def setHudPreferencesTool(showShape, toolColorStopped, toolColorSpinning):
    '''Set HUD tool preferences.'''
    pref = preferences()
    pref.SetBool(PreferenceHudFontSize, showShape)
    pref.SetUnsigned(PreferenceHudToolColorStopped, toolColorStopped.rgba())
    pref.SetUnsigned(PreferenceHudToolColorSpinning, toolColorSpinning.rgba())

def setHudPreferencesProgr(hide, bar, percent, elapsed, remaining, total, fontName, fontSize, color):
    '''Set HUD progress preferences.'''
    pref = preferences()
    pref.SetBool(PreferenceHudProgrHide,        hide)
    pref.SetBool(PreferenceHudProgrBar,         bar)
    pref.SetBool(PreferenceHudProgrPercent,     percent)
    pref.SetBool(PreferenceHudProgrElapsed,     elapsed)
    pref.SetBool(PreferenceHudProgrRemaining,   remaining)
    pref.SetBool(PreferenceHudProgrTotal,       total)
    pref.SetString(PreferenceHudProgrFontName,  fontName)
    pref.SetInt(PreferenceHudProgrFontSize,     fontSize)
    pref.SetUnsigned(PreferenceHudProgrColor,   color.rgba())

class PageGeneral(object):
    '''A class managing the general Preferences editor for the Machinekit workbench.'''

    AdditionalItemLabel = '<click-to-edit>'

    def __init__(self, parent=None):
        import FreeCADGui
        import machinekit
        self.form = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('preferences.ui'))
        self.form.restServers.itemChanged.connect(self.itemChanged)

    def saveSettings(self):
        '''Store preferences from the UI back to the model so they can be saved.'''
        import machinekit
        servers = []
        for row in range(self.form.restServers.count()):
            s = self.form.restServers.item(row).text()
            if s and s != self.AdditionalItemLabel:
                servers.append(s)
        setGeneralPreferences(self.form.startOnLoad.isChecked(), self.form.addToPathWB.isChecked(), servers)
        for mk in machinekit.Instances():
            mk.preferencesUpdate.emit()

    def _addItem(self, label):
        import PySide.QtGui, PySide.QtCore
        item = PySide.QtGui.QListWidgetItem(label)
        item.setFlags(PySide.QtCore.Qt.ItemFlag.ItemIsEnabled | PySide.QtCore.Qt.ItemFlag.ItemIsSelectable | PySide.QtCore.Qt.ItemFlag.ItemIsEditable)
        self.form.restServers.addItem(item)

    def loadSettings(self):
        '''Load preferences and update the eitor accordingly.'''
        self.form.startOnLoad.setChecked(startOnLoad())
        self.form.addToPathWB.setChecked(addToPathWB())
        self.form.restServers.blockSignals(True)
        for server in sorted(restServers()):
            self._addItem(server)
        self._addItem(self.AdditionalItemLabel)
        self.form.restServers.blockSignals(False)

    def itemChanged(self, item):
        self.form.restServers.blockSignals(True)
        if item.text() and self.form.restServers.currentRow() == (self.form.restServers.count() - 1):
            self._addItem(self.AdditionalItemLabel)
        elif not item.text():
            item.setText(self.AdditionalItemLabel)
        self.form.restServers.blockSignals(False)

class PageHUD(object):
    '''A class managing the HUD Preferences editor for the Machinekit workbench.'''

    def __init__(self, parent=None):
        import FreeCADGui
        import machinekit
        self.form = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('preferences-hud.ui'))

    def saveSettings(self):
        '''Store preferences from the UI back to the model so they can be saved.'''
        import machinekit
        setHudPreferences(self.form.workCoordinates.isChecked(), self.form.machineCoordinates.isChecked())
        setHudPreferencesFont(self.form.fontName.currentFont().family(), self.form.fontSize.value(), self.form.fontColorUnhomed.property('color'), self.form.fontColorHomed.property('color'))
        setHudPreferencesTool(self.form.toolShowShape.isChecked(), self.form.toolColorStopped.property('color'), self.form.toolColorSpinning.property('color'))
        setHudPreferencesProgr(self.form.progrHide.isChecked(), self.form.progrBar.isChecked(), self.form.progrPercent.isChecked(), self.form.progrElapsed.isChecked(), self.form.progrRemaining.isChecked(), self.form.progrTotal.isChecked(), self.form.progrFontName.currentFont().family(), self.form.progrFontSize.value(), self.form.progrColor.property('color'))
        for mk in machinekit.Instances():
            mk.preferencesUpdate.emit()

    def loadSettings(self):
        '''Load preferences and update the eitor accordingly.'''
        import PySide.QtGui
        self.form.workCoordinates.setChecked(hudShowWorkCoordinates())
        self.form.machineCoordinates.setChecked(hudShowMachineCoordinates())

        self.form.fontSize.setValue(hudFontSize())
        self.form.fontName.setCurrentFont(PySide.QtGui.QFont(hudFontName()))
        self.form.fontColorUnhomed.setProperty('color', PySide.QtGui.QColor.fromRgba(hudFontColorUnhomed(True)))
        self.form.fontColorHomed.setProperty('color', PySide.QtGui.QColor.fromRgba(hudFontColorHomed(True)))

        self.form.toolShowShape.setChecked(hudToolShowShape())
        self.form.toolColorStopped.setProperty('color', PySide.QtGui.QColor.fromRgba(hudToolColorStopped(True)))
        self.form.toolColorSpinning.setProperty('color', PySide.QtGui.QColor.fromRgba(hudToolColorSpinning(True)))

        self.form.progrHide.setChecked(hudProgrHide())
        self.form.progrBar.setChecked(hudProgrBar())
        self.form.progrPercent.setChecked(hudProgrPercent())
        self.form.progrElapsed.setChecked(hudProgrElapsed())
        self.form.progrRemaining.setChecked(hudProgrRemaining())
        self.form.progrTotal.setChecked(hudProgrTotal())
        self.form.progrFontSize.setValue(hudProgrFontSize())
        self.form.progrFontName.setCurrentFont(PySide.QtGui.QFont(hudProgrFontName()))
        self.form.progrColor.setProperty('color', PySide.QtGui.QColor.fromRgba(hudProgrColor(True)))

_setup = False

def Setup():
    global _setup
    if not _setup:
        import FreeCADGui
        import machinekit

        icon = machinekit.FileResource('machinekiticon.svg')
        FreeCADGui.addIcon('preferences-machinekit', icon)
        FreeCADGui.addPreferencePage(PageGeneral, 'Machinekit')
        FreeCADGui.addPreferencePage(PageHUD,     'Machinekit')
        _setup = True

