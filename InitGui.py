class MachinekitWorkbench(Workbench):
    '''Registration and loading of the Machinekit workbench'''
    import machinekit
    Icon = machinekit.FileResource('machinekiticon.svg')
    MenuText = "Machinekit"
    ToolTip = "Workbench to interact with machinkit controlling a CNC"

    def Initialize(self):
        import MachinekitPreferences
        MachinekitPreferences.Setup()

        import MachinekitCommands
        MachinekitCommands.SetupToolbar(self)
        MachinekitCommands.SetupMenu(self)

    def Activated(self):
        import MachinekitCommands
        MachinekitCommands.Activated()

    def Deactivated(self):
        import MachinekitCommands
        MachinekitCommands.Deactivated()

Gui.addWorkbench(MachinekitWorkbench)

import MachinekitPreferences
if MachinekitPreferences.startOnLoad():
    import MachinekitCommands
    MachinekitCommands.Activated()
