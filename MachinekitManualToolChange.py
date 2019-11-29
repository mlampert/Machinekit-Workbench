import MKCommand
import PathScripts.PathLog as PathLog
import PySide.QtCore
import PySide.QtGui
import machinekit

#PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
#PathLog.trackModule(PathLog.thisModule())

class Controller(object):
    '''Class to prompt user to perform a tool change and confirm its completion.'''
    def __init__(self, mk):
        self.mk = mk
        self.mk.halUpdate.connect(self.changed)

    def isConnected(self):
        '''Return True if MK is connected and responsive.'''
        return self.mk['halrcomp'] and self.mk['halrcmd']

    def changed(self, service, msg):
        '''If MK's update includes a request for a tool change, present the user with
        a dialog box and ask for confirmation.
        On successful tool change update MK accordingly - if the user cancels the tool
        change abort the task in progress in MK.'''
        if msg.changeTool():
            if 0 == msg.toolNumber():
                PathLog.debug("TC clear")
                service.toolChanged(self.mk['halrcmd'], True)
            else:
                tc = self.getTC(msg.toolNumber())
                if tc:
                    msg = [self.mk.name(), '', "Insert tool #%d" % tc.ToolNumber, "<i><b>\"%s\"</b></i>" % tc.Label]
                else:
                    msg = [self.mk.name(), '', "Insert tool <b>#%d</b>" % msg.toolNumber()]
                mb = PySide.QtGui.QMessageBox()
                mb.setWindowIcon(machinekit.IconResource('machinekiticon.svg'))
                mb.setWindowTitle('Machinekit')
                mb.setTextFormat(PySide.QtCore.Qt.TextFormat.RichText)
                mb.setText("<div align='center'>%s</div>" % '<br/>'.join(msg))
                mb.setIcon(PySide.QtGui.QMessageBox.Warning)
                mb.setStandardButtons(PySide.QtGui.QMessageBox.Ok | PySide.QtGui.QMessageBox.Abort)
                if PySide.QtGui.QMessageBox.Ok == mb.exec_():
                    PathLog.debug("TC confirm")
                    service.toolChanged(self.mk['halrcmd'], True)
                else:
                    PathLog.debug("TC abort")
                    self.mk['command'].sendCommand(MKCommand.MKCommandTaskAbort())
        elif msg.toolChanged():
            PathLog.debug('TC reset')
            service.toolChanged(self.mk['halrcmd'], False)
        else:
            PathLog.debug('TC -')
            pass

    def getTC(self, nr):
        '''getTC(nr) ... helper function to find the specified TC in the job loaded in MK.'''
        job = self.mk.getJob()
        if job:
            for tc in job.ToolController:
                if tc.ToolNumber == nr:
                    return tc
        return None

