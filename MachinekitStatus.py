# Display and change of miscellaneous states

import FreeCAD
import FreeCADGui
import MKUtils
import MachinekitManualToolChange
import PathScripts.PathLog as PathLog
import PathScripts.PathPost as PathPost
import PathScripts.PathUtil as PathUtil
import PySide.QtCore
import PySide.QtGui
import ftplib
import io
import machinekit
import machinetalk.protobuf.motcmds_pb2 as MOTCMDS
import machinetalk.protobuf.status_pb2 as STATUS
import machinetalk.protobuf.types_pb2 as TYPES

from MKCommand import *
from MKServiceCommand import *


#PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
#PathLog.trackModule(PathLog.thisModule())

class Status(object):
    '''A class used by the Combo view to interact with the MK instance itself.
    Currently it's only used to turn MK on/off and home the axes.'''


    def __init__(self, mk):
        self.mk = mk
        self.ui = FreeCADGui.PySideUic.loadUi(machinekit.FileResource('status.ui'), self)
        palette = PySide.QtGui.QPalette()
        palette.setColor(PySide.QtGui.QPalette.Background, PySide.QtGui.QColor(0xffd75e))
        self.ui.dockWidgetContents.setAutoFillBackground(True)
        self.ui.dockWidgetContents.setPalette(palette)

        self.ui.statusEStop.clicked.connect(self.toggleEstop)
        self.ui.statusPower.clicked.connect(self.togglePower)
        self.ui.statusHome.clicked.connect(self.toggleHomed)

        self.updateUI()
        self.mk.statusUpdate.connect(self.changed)

    def terminate(self):
        self.mk.statusUpdate.disconnect(self.changed)
        self.mk = None

    def toggleEstop(self):
        self.mk['command'].sendCommands([MKCommandEstop(not self.mk['status.io.estop'])])

    def togglePower(self):
        self.mk.power()

    def toggleHomed(self):
        if self.mk.isHomed():
            sequence = [[cmd] for cmd in MKUtils.taskModeManual(self.mk['status'])]
            commands = []
            for axis in self.mk['status.config.axis']:
                commands.append(MKCommandAxisHome(axis.index, False))
            sequence.append(commands)
            self.mk['command'].sendCommandSequence(sequence)
        else:
            self.mk.home()

    def updateUI(self):
        if self.mk.isValid():
            self.ui.dockWidgetContents.setEnabled(True)
            self.ui.statusEStop.setChecked(self.mk['status.io.estop'])
            self.ui.statusPower.setChecked(self.mk.isPowered())
            self.ui.statusHome.setChecked(self.mk.isHomed())
            self.ui.statusHome.setEnabled(self.mk.isPowered())

            self.ui.statusTaskMode.setText(STATUS.EmcTaskModeType.Name(self.mk['status.task.task.mode']).split('_')[-1])
            self.ui.statusVx.setText("%7.2f" % self.mk['status.motion.axis.0.velocity'])
            self.ui.statusVy.setText("%7.2f" % self.mk['status.motion.axis.1.velocity'])
            self.ui.statusVz.setText("%7.2f" % self.mk['status.motion.axis.2.velocity'])
            self.ui.statusV.setText("%7.2f" % self.mk['status.motion.current_vel'])
        else:
            self.ui.dockWidgetContents.setEnabled(False)

    def changed(self, service, updated):
        if self.mk:
            self.updateUI()
