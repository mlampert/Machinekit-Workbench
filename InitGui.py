class MachinekitWorkbench(Workbench):
    "Test workbench object"
    import machinekit
    Icon = machinekit.FileResource('machinekiticon.svg')
    MenuText = "Machinekit"
    ToolTip = "Workbench to interact with machinkit controlling a CNC"

    def Initialize(self):
        import FreeCADGui
        import MachinekitPreferences
        FreeCADGui.addPreferencePage(MachinekitPreferences.Page, 'Machinekit')
        FreeCADGui.addIcon('preferences-machinekit', self.Icon)

        import MachinekitCommands
        MachinekitCommands.SetupToolbar(self)
        MachinekitCommands.SetupMenu(self)
        pass

    def Activated(self):
        import MachinekitCommands
        MachinekitCommands.Activated()

    def Deactivated(self):
        import MachinekitCommands
        MachinekitCommands.Deactivated()

Gui.addWorkbench(MachinekitWorkbench)
