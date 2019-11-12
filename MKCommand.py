# Classes implementing the different commands that can be sent to MK
# The implemented classes do not cover the complete functional set of MK
# but are what is required to implement a basic UI.

import enum
import machinetalk.protobuf.message_pb2 as MESSAGE
import machinetalk.protobuf.status_pb2  as STATUS
import machinetalk.protobuf.types_pb2   as TYPES

class MKCommandStatus(enum.Enum):
    '''An enumeration used to track a command through its entire lifetime.'''
    Created   = 0
    Sent      = 1
    Executed  = 2
    Completed = 3
    Obsolete  = 4

class MKCommand(object):
    '''Base class for all commands implementing the general framework.'''

    def __init__(self, command):
        self.msg = MESSAGE.Container()
        self.msg.type = command
        self.state = MKCommandStatus.Created

    def __str__(self):
        return self.__class__.__name__

    def expectsResponses(self):
        '''Overwrite and return False if the specific command does not get a response message.
        Most commands do get a response so the default is to return True'''
        return True

    def serializeToString(self):
        return self.msg.SerializeToString()

    def msgSent(self):
        '''Called by the framework when the command was sent to MK'''
        self.state = MKCommandStatus.Sent
    def msgExecuted(self):
        '''Called by the framework when the command was executed by MK'''
        self.state = MKCommandStatus.Executed
    def msgCompleted(self):
        '''Called by the framework when the command has completed'''
        self.state = MKCommandStatus.Completed
    def msgObsolete(self):
        '''Called by the framework when the command has become obsolete'''
        self.state = MKCommandStatus.Obsolete

    def isExecuted(self):
        '''Returns True if the command has been executed by MK'''
        return self.state in [MKCommandStatus.Executed, MKCommandStatus.Completed]
    def isCompleted(self):
        '''Returns True if the command has completed'''
        return self.state == MKCommandStatus.Completed
    def isObsolete(self):
        '''Returns True if the command is obsolete and can be removed'''
        return self.state == MKCommandStatus.Obsolete

    def statusString(self):
        '''Return command's status as string.'''
        return self.state.name

class MKCommandExecute(MKCommand):
    '''Base class for all commands sent to the 'execute' interpreter.'''
    def __init__(self, command):
        MKCommand.__init__(self, command)
        self.msg.interp_name = 'execute'

class MKCommandPreview(MKCommand):
    '''Base class for all commands sent to the 'preview' interpreter.'''
    def __init__(self, command):
        MKCommand.__init__(self, command)
        self.msg.interp_name = 'preview'

class MKCommandTaskSetState(MKCommandExecute):
    '''Base class for setting the state of task variables.'''
    def __init__(self, state):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_SET_STATE)
        self.msg.emc_command_params.task_state = state

class MKCommandEstop(MKCommandTaskSetState):
    '''Command to engage or disengage the E-Stop.
    on=True means the E-Stop is pressed and MK will ignore all other commands.'''
    def __init__(self, on):
        MKCommandTaskSetState.__init__(self, STATUS.EMC_TASK_STATE_ESTOP if on else STATUS.EMC_TASK_STATE_ESTOP_RESET)

class MKCommandPower(MKCommandTaskSetState):
    '''Command to power MK on or off.'''
    def __init__(self, on):
        MKCommandTaskSetState.__init__(self, STATUS.EMC_TASK_STATE_ON if on else STATUS.EMC_TASK_STATE_OFF)

class MKCommandOpenFile(MKCommand):
    '''Command to open a file, either for 'executing' it or for 'previewing' it.'''
    def __init__(self, filename, preview):
        if preview:
            MKCommandPreview.__init__(self, TYPES.MT_EMC_TASK_PLAN_OPEN)
        else:
            MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_OPEN)
        self.msg.emc_command_params.path = filename

class MKCommandTaskRun(MKCommand):
    '''Command to start execution of the currently opened file - or to display its preview.'''
    def __init__(self, preview, line=0):
        if preview:
            MKCommandPreview.__init__(self, TYPES.MT_EMC_TASK_PLAN_RUN)
        else:
            MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_RUN)
        self.msg.emc_command_params.line_number = line
        self.preview = preview

    def expectsResponses(self):
        return not self.preview

class MKCommandTaskStep(MKCommandExecute):
    '''Command to execute a single step of the current task (from its current line).'''
    def __init__(self):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_STEP)

class MKCommandTaskPause(MKCommandExecute):
    '''Command to pause execution of the current task.'''
    def __init__(self):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_PAUSE)

class MKCommandTaskResume(MKCommandExecute):
    '''Command to resume a currently paused task.'''
    def __init__(self):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_RESUME)

class MKCommandTaskReset(MKCommandExecute):
    '''Command to reset task execution. This clears any paused state and resets progress to line 0.'''
    def __init__(self, preview):
        if preview:
            MKCommandPreview.__init__(self, TYPES.MT_EMC_TASK_PLAN_INIT)
        else:
            MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_INIT)

class MKCommandAxisHome(MKCommand):
    '''Command to initiate homing (or unhoming) of a gifen axis.
    The homing itself is done by MK without any need of interaction. The staging and sequencing
    of homing multiple axes has to be orchestrated by the UI though.'''
    def __init__(self, index, home=True):
        MKCommand.__init__(self, TYPES.MT_EMC_AXIS_HOME if home else TYPES.MT_EMC_AXIS_UNHOME)
        self.msg.emc_command_params.index = index

    def __str__(self):
        return "MKCommandAxisHome[%d]" % (self.msg.emc_command_params.index)

class MKCommandTaskExecute(MKCommandExecute):
    '''Command for executing arbitrary commands and command sequences.'''
    def __init__(self, cmd):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_EXECUTE)
        self.msg.emc_command_params.command = cmd

class MKCommandTaskSetMode(MKCommandExecute):
    '''Command to set a specific task mode. Valid modes are:
    * STATUS.EmcTaskModeType.EMC_TASK_MODE_AUTO   ... required for the execute interpreter to take control
    * STATUS.EmcTaskModeType.EMC_TASK_MODE_MDI    ... required to issue individual g-code commands
    * STATUS.EmcTaskModeType.EMC_TASK_MODE_MANUAL ... required for jogging
    '''
    def __init__(self, mode):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_SET_MODE)
        self.msg.emc_command_params.task_mode = mode

class MKCommandTaskAbort(MKCommandExecute):
    '''Command to abort the current task.'''
    def __init__(self):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_ABORT)

class MKCommandAxisAbort(MKCommandExecute):
    '''Command to abort the current axis command - mostly used to stop the active jogging command.'''
    def __init__(self, index):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_AXIS_ABORT)
        self.msg.emc_command_params.index = index

class MKCommandAxisJog(MKCommandExecute):
    '''Command to initiate jogging.
    There are two different types of jog, distance and incremental.

    Incremental jogging initiates the jog which will continue until either
    a new jog command is sent or a MKCommandAxisAbort command is sent. This puts some
    requirements on the UI's reliability and capability of sending that termination
    command.

    Distance jogging is marginally safer because MK will silently ignore
    a distance jog if it exceeds the axis' limit. There is no indication that the
    command was not executed and the tool is still at the same position as it was
    before, making the next jog a risky manouver. This is important for scripted jog
    sequences like a contour around the tasks boundaries.

    It is the UI's responsibility to extract proper values for velocity and distance.
    '''

    def __init__(self, index, velocity, distance = None):
        self.index = index
        self.velocity = velocity
        self.distance = distance

        if distance is None:
            MKCommandExecute.__init__(self, TYPES.MT_EMC_AXIS_JOG)
        else:
            MKCommandExecute.__init__(self, TYPES.MT_EMC_AXIS_INCR_JOG)
            self.msg.emc_command_params.distance = distance
        self.msg.emc_command_params.index = index
        self.msg.emc_command_params.velocity = velocity

    def __str__(self):
        if self.distance:
            return "AxisJog(%d, %.2f, %.2f)" % (self.index, self.velocity, self.distance)
        return "AxisJog(%d, %.2f, -)" % (self.index, self.velocity)

class MKCommandTrajSetScale(MKCommand):
    '''Command to overwrite the feed rate or rapid speed of the tool bit. scale is a multiplier of the configured speed.'''
    def __init__(self, scale, rapid=False):
        if rapid:
            MKCommand.__init__(self, TYPES.MT_EMC_TRAJ_SET_RAPID_SCALE)
        else:
            MKCommand.__init__(self, TYPES.MT_EMC_TRAJ_SET_SCALE)
        self.msg.emc_command_params.scale = scale

