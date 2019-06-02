class MachinekitWorkbench(Workbench):
	"Test workbench object"
	Icon = FreeCAD.getHomePath() + "Mod/Machinekit/Resources/machinekiticon.png"
	MenuText = "Machinekit"
	ToolTip = "Workbench to interact with machinkit controlling a CNC"
	
	def Initialize(self):
		#import Commands
		#self.appendToolbar("TemplateTools",["TemplatePyMod_Cmd1","TemplatePyMod_Cmd2","TemplatePyMod_Cmd3","TemplatePyMod_Cmd4","TemplatePyMod_Cmd5"])
		#menu = ["ModulePy &Commands","PyModuleCommands"]
		#list = ["TemplatePyMod_Cmd1","TemplatePyMod_Cmd2","TemplatePyMod_Cmd3","TemplatePyMod_Cmd5","TemplatePyMod_Cmd6"]
		#self.appendCommandbar("PyModuleCommands",list)
		#self.appendMenu(menu,list)
		pass

	def Activated(self):
	    pass
	def Deactivated(self):
	    pass


Gui.addWorkbench(MachinekitWorkbench)
