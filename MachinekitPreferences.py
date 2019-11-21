# Classes and functions to deal with the Machinkit workbench's preferences

import FreeCAD

PreferenceStartOnLoad = 'GeneralStartOnLoad'
PreferenceAddToPathWB = 'GeneralAddToPathWB'

PreferenceHudWorkCoordinates = "HudWorkCoordinates"
PreferenceHudMachineCoordinates = "HudMachineCoordinates"

PreferenceHudFontName  = "HudFontName"
PreferenceHudFontSize  = "HudFontSize"
PreferenceHudFontColorUnhomed = "HudFontColorUnhomed"
PreferenceHudFontColorHomed   = "HudFontColorHomed"

PreferenceHudToolShowShape     = "HudToolShowShape"
PreferenceHudToolColorStopped  = "HudToolColorStopped"
PreferenceHudToolColorSpinning = "HudToolColorSpinning"

def preferences():
    '''Return the FC MK workbench preferences.'''
    return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Machinekit")

def startOnLoad():
    '''Return True if 'start on load' is enabled (the default).'''
    return preferences().GetBool(PreferenceStartOnLoad, True)

def addToPathWB():
    '''Return True if MK Combo commands should be added to the Path workbench toolbar (the default).'''
    return preferences().GetBool(PreferenceAddToPathWB, True)

def setGeneralPreferences(start, pathWB):
    '''API to set the general preferences.'''
    pref = preferences()
    pref.SetBool(PreferenceStartOnLoad, start)
    pref.SetBool(PreferenceAddToPathWB, pathWB)

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
    return _color(PreferenceHudFontColorUnhomed, 0xffe600e6, raw)

def hudFontColorHomed(raw=False):
    '''Return the configured HUD font color to be used when the tool IS homed.'''
    return _color(PreferenceHudFontColorHomed, 0xff00e600, raw)

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


class Page(object):
    '''A class managing the Preferences editor for the Machinekit workbench.'''

    def __init__(self, parent=None):
        import FreeCADGui
        import machinekit
        self.form = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('preferences.ui'))

    def saveSettings(self):
        '''Store preferences from the UI back to the model so they can be saved.'''
        import machinekit
        setGeneralPreferences(self.form.startOnLoad.isChecked(), self.form.addToPathWB.isChecked())
        setHudPreferences(self.form.workCoordinates.isChecked(), self.form.machineCoordinates.isChecked())
        setHudPreferencesFont(self.form.fontName.currentFont().family(), self.form.fontSize.value(), self.form.fontColorUnhomed.property('color'), self.form.fontColorHomed.property('color'))
        setHudPreferencesTool(self.form.toolShowShape.isChecked(), self.form.toolColorStopped.property('color'), self.form.toolColorSpinning.property('color'))
        for mk in machinekit.Instances():
            mk.preferencesUpdate.emit()

    def loadSettings(self):
        '''Load preferences and update the eitor accordingly.'''
        import PySide.QtGui
        self.form.startOnLoad.setChecked(startOnLoad())
        self.form.addToPathWB.setChecked(addToPathWB())

        self.form.workCoordinates.setChecked(hudShowWorkCoordinates())
        self.form.machineCoordinates.setChecked(hudShowMachineCoordinates())

        self.form.fontSize.setValue(hudFontSize())
        self.form.fontName.setCurrentFont(PySide.QtGui.QFont(hudFontName()))
        self.form.fontColorUnhomed.setProperty('color', PySide.QtGui.QColor.fromRgba(hudFontColorUnhomed(True)))
        self.form.fontColorHomed.setProperty('color', PySide.QtGui.QColor.fromRgba(hudFontColorHomed(True)))

        self.form.toolShowShape.setChecked(hudToolShowShape())
        self.form.toolColorStopped.setProperty('color', PySide.QtGui.QColor.fromRgba(hudToolColorStopped(True)))
        self.form.toolColorSpinning.setProperty('color', PySide.QtGui.QColor.fromRgba(hudToolColorSpinning(True)))

_setup = False

def Setup():
    global _setup
    if not _setup:
        import FreeCADGui
        import machinekit

        icon = machinekit.FileResource('machinekiticon.svg')
        FreeCADGui.addPreferencePage(Page, 'Machinekit')
        FreeCADGui.addIcon('preferences-machinekit', icon)
        _setup = True

