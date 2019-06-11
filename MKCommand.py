import enum
import machinetalk.protobuf.message_pb2 as MESSAGE
import machinetalk.protobuf.status_pb2  as STATUS
import machinetalk.protobuf.types_pb2   as TYPES

class MKCommandStatus(enum.Enum):
    Created   = 0
    Sent      = 1
    Executed  = 2
    Completed = 3
    Obsolete  = 4

class MKCommand(object):
    def __init__(self, command):
        self.msg = MESSAGE.Container()
        self.msg.type = command
        self.state = MKCommandStatus.Created

    def __str__(self):
        return self.__class__.__name__

    def expectsResponses(self):
        return True

    def serializeToString(self):
        return self.msg.SerializeToString()

    def msgSent(self):
        self.state = MKCommandStatus.Sent
    def msgExecuted(self):
        self.state = MKCommandStatus.Executed
    def msgCompleted(self):
        self.state = MKCommandStatus.Completed
    def msgObsolete(self):
        self.state = MKCommandStatus.Obsolete

    def isExecuted(self):
        return self.state in [MKCommandStatus.Executed, MKCommandStatus.Completed]
    def isCompleted(self):
        return self.state == MKCommandStatus.Completed
    def isObsolete(self):
        return self.state == MKCommandStatus.Obsolete

    def statusString(self):
        return self.state.name

class MKCommandExecute(MKCommand):
    def __init__(self, command):
        MKCommand.__init__(self, command)
        self.msg.interp_name = 'execute'

class MKCommandPreview(MKCommand):
    def __init__(self, command):
        MKCommand.__init__(self, command)
        self.msg.interp_name = 'preview'

class MKCommandTaskSetState(MKCommandExecute):
    def __init__(self, state):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_SET_STATE)
        self.msg.emc_command_params.task_state = state

class MKCommandEstop(MKCommandTaskSetState):
    def __init__(self, on):
        MKCommandTaskSetState.__init__(self, STATUS.EMC_TASK_STATE_ESTOP if on else STATUS.EMC_TASK_STATE_ESTOP_RESET)

class MKCommandPower(MKCommandTaskSetState):
    def __init__(self, on):
        MKCommandTaskSetState.__init__(self, STATUS.EMC_TASK_STATE_ON if on else STATUS.EMC_TASK_STATE_OFF)

class MKCommandOpenFile(MKCommand):
    def __init__(self, filename, preview):
        if preview:
            MKCommandPreview.__init__(self, TYPES.MT_EMC_TASK_PLAN_OPEN)
        else:
            MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_OPEN)
        self.msg.emc_command_params.path = filename

class MKCommandTaskRun(MKCommand):
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
    def __init__(self):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_STEP)

class MKCommandTaskPause(MKCommandExecute):
    def __init__(self):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_PAUSE)

class MKCommandTaskResume(MKCommandExecute):
    def __init__(self):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_RESUME)

class MKCommandTaskReset(MKCommandExecute):
    def __init__(self, preview):
        if preview:
            MKCommandPreview.__init__(self, TYPES.MT_EMC_TASK_PLAN_INIT)
        else:
            MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_INIT)

class MKCommandAxisHome(MKCommand):
    def __init__(self, index, home=True):
        MKCommand.__init__(self, TYPES.MT_EMC_AXIS_HOME if home else TYPES.MT_EMC_AXIS_UNHOME)
        self.msg.emc_command_params.index = index

    def __str__(self):
        return "MKCommandAxisHome[%d]" % (self.msg.emc_command_params.index)

class MKCommandTaskExecute(MKCommandExecute):
    def __init__(self, cmd):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_PLAN_EXECUTE)
        self.msg.emc_command_params.command = cmd

class MKCommandTaskSetMode(MKCommandExecute):
    def __init__(self, mode):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_SET_MODE)
        self.msg.emc_command_params.task_mode = mode

class MKCommandTaskAbort(MKCommandExecute):
    def __init__(self):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_TASK_ABORT)

class MKCommandAxisAbort(MKCommandExecute):
    def __init__(self, index):
        MKCommandExecute.__init__(self, TYPES.MT_EMC_AXIS_ABORT)
        self.msg.emc_command_params.index = index

class MKCommandAxisJog(MKCommandExecute):
    def __init__(self, index, velocity, distance = None):
        if distance is None:
            MKCommandExecute.__init__(self, TYPES.MT_EMC_AXIS_JOG)
        else:
            MKCommandExecute.__init__(self, TYPES.MT_EMC_AXIS_INCR_JOG)
            self.msg.emc_command_params.distance = distance
        self.msg.emc_command_params.index = index
        self.msg.emc_command_params.velocity = velocity
