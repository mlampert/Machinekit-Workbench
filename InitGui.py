class MachinekitWorkbench(Workbench):
    "Test workbench object"
    import machinekit
    Icon = machinekit.FileResource('machinekiticon.png')
    MenuText = "Machinekit"
    ToolTip = "Workbench to interact with machinkit controlling a CNC"

    def Initialize(self):
        import MachinekitCommands
        self.appendToolbar(MachinekitCommands.ToolbarName, MachinekitCommands.ToolbarTools)
        #menu = ["ModulePy &Commands","PyModuleCommands"]
        #list = ["TemplatePyMod_Cmd1","TemplatePyMod_Cmd2","TemplatePyMod_Cmd3","TemplatePyMod_Cmd5","TemplatePyMod_Cmd6"]
        #self.appendCommandbar("PyModuleCommands",list)
        #self.appendMenu(menu,list)
        pass

    def Activated(self):
        import MachinekitCommands
        MachinekitCommands.Activated()

    def Deactivated(self):
        import MachinekitCommands
        MachinekitCommands.Deactivated()

Gui.addWorkbench(MachinekitWorkbench)
