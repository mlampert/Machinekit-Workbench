class MachinekitWorkbench(Workbench):
    "Test workbench object"
    import machinekit
    Icon = machinekit.FileResource('machinekiticon.png')
    MenuText = "Machinekit"
    ToolTip = "Workbench to interact with machinkit controlling a CNC"

    def Initialize(self):
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
