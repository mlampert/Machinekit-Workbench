import FreeCAD

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
    return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Machinekit")

def hudFontName():
    return preferences().GetString(PreferenceHudFontName, 'mono')

def hudFontSize():
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
    return _color(PreferenceHudFontColorUnhomed, 0xffe600e6, raw)

def hudFontColorHomed(raw=False):
    return _color(PreferenceHudFontColorHomed, 0xff00e600, raw)

def hudShowWorkCoordinates():
    return preferences().GetBool(PreferenceHudWorkCoordinates, True)

def hudShowMachineCoordinates():
    return preferences().GetBool(PreferenceHudMachineCoordinates, False)

def hudToolShowShape():
    return preferences().GetBool(PreferenceHudToolShowShape, True)

def hudToolColorStopped(raw=False):
    return _color(PreferenceHudToolColorStopped, 0xff0000e5, raw)

def hudToolColorSpinning(raw=False):
    return _color(PreferenceHudToolColorSpinning, 0xffe50000, raw)

def setHudPreferences(workCoordinates, machineCoordinates):
    pref = preferences()
    pref.SetBool(PreferenceHudWorkCoordinates, workCoordinates)
    pref.SetBool(PreferenceHudMachineCoordinates, machineCoordinates)

def setHudPreferencesFont(fontName, fontSize, fontColorUnhomed, fontColorHomed):
    pref = preferences()
    pref.SetInt(PreferenceHudFontSize, fontSize)
    pref.SetString(PreferenceHudFontName, fontName)
    pref.SetUnsigned(PreferenceHudFontColorUnhomed, fontColorUnhomed.rgba())
    pref.SetUnsigned(PreferenceHudFontColorHomed, fontColorHomed.rgba())

def setHudPreferencesTool(showShape, toolColorStopped, toolColorSpinning):
    pref = preferences()
    pref.SetBool(PreferenceHudFontSize, showShape)
    pref.SetUnsigned(PreferenceHudToolColorStopped, toolColorStopped.rgba())
    pref.SetUnsigned(PreferenceHudToolColorSpinning, toolColorSpinning.rgba())


class Page:

    def __init__(self, parent=None):
        import FreeCADGui
        import machinekit
        self.form = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('preferences.ui'))

    def saveSettings(self):
        import machinekit
        setHudPreferences(self.form.workCoordinates.isChecked(), self.form.machineCoordinates.isChecked())
        setHudPreferencesFont(self.form.fontName.currentFont().family(), self.form.fontSize.value(), self.form.fontColorUnhomed.property('color'), self.form.fontColorHomed.property('color'))
        setHudPreferencesTool(self.form.toolShowShape.isChecked(), self.form.toolColorStopped.property('color'), self.form.toolColorSpinning.property('color'))
        for mk in machinekit.Instances():
            mk.preferencesUpdate.emit()

    def loadSettings(self):
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

