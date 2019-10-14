import FreeCAD

PreferenceHudFontName = "HudFontName"
PreferenceHudFontSize = "HudFontSize"
PreferenceHudWorkCoordinates = "HudWorkCoordinates"
PreferenceHudMachineCoordinates = "HudMachineCoordinates"

def preferences():
    return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Machinekit")

def hudFontName():
    return preferences().GetString(PreferenceHudFontName, 'mono')

def hudFontSize():
    return preferences().GetInt(PreferenceHudFontSize, 33)

def hudShowWorkCoordinates():
    return preferences().GetBool(PreferenceHudWorkCoordinates, True)

def hudShowMachineCoordinates():
    return preferences().GetBool(PreferenceHudMachineCoordinates, False)

def setHudPreferences(workCoordinates, machineCoordinates, fontSize, fontName):
    pref = preferences()
    pref.SetBool(PreferenceHudWorkCoordinates, workCoordinates)
    pref.SetBool(PreferenceHudMachineCoordinates, machineCoordinates)
    pref.SetInt(PreferenceHudFontSize, fontSize)
    pref.SetString(PreferenceHudFontName, fontName)

class Page:

    def __init__(self, parent=None):
        import FreeCADGui
        import machinekit
        self.form = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('preferences.ui'))

    def saveSettings(self):
        import machinekit
        setHudPreferences(self.form.workCoordinates.isChecked(), self.form.machineCoordinates.isChecked(), self.form.fontSize.value(), self.form.fontName.currentFont().family())
        for mk in machinekit.Instances():
            mk.preferencesUpdate.emit()

    def loadSettings(self):
        import PySide.QtGui
        self.form.workCoordinates.setChecked(hudShowWorkCoordinates())
        self.form.machineCoordinates.setChecked(hudShowMachineCoordinates())
        self.form.fontSize.setValue(hudFontSize())
        self.form.fontName.setCurrentFont(PySide.QtGui.QFont(hudFontName()))
