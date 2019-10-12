import PathScripts.PathLog as PathLog
import traceback

from MKObserverable import *
from MKService import *

from machinetalk.protobuf.status_pb2 import *
from machinetalk.protobuf.types_pb2 import MT_EMCSTAT_FULL_UPDATE


PathLog.setLevel(PathLog.Level.NOTICE, PathLog.thisModule())
#PathLog.trackModule(PathLog.thisModule())

class MKServiceContainer(MKObserverable):
    def __init__(self, valid):
        super().__init__()
        self.valid = valid

    def __getitem__(self, path):
        if self.valid:
            try:
                attr = self.__getattribute__(path[0])
                return returnAttribute(attr, path[1:])
            except:
                PathLog.error("unknown container path = %s (%s)" % (path, self))
                traceback.print_stack()
                raise
        return None

class minmax(MKServiceContainer):
    def __init__(self, min, max, default=None):
        super().__init__(True)
        self.min = min
        self.max = max
        self.default = default

def mergeMinMax(mm, name, proto, attr, default=None):
    maxAttr = "max_%s" % attr
    minAttr = "min_%s" % attr

    if '' == default:
        default = "default_%s" % attr

    updated = []
    if proto.HasField(minAttr):
        mm.min = proto.__getattribute__(minAttr)
        updated.append("%s.min" % name)
    if proto.HasField(maxAttr):
        mm.max = proto.__getattribute__(maxAttr)
        updated.append("%s.max" % name)
    if not default is None:
        if proto.HasField(default):
            mm.default = proto.__getattribute__(default)
            updated.append("%s.default" % name)

    return updated

def defaultPosition():
    return {'x':0.0, 'y':0.0, 'z':0.0, 'a':0.0, 'b':0.0, 'c':0.0, 'u':0.0, 'v':0.0, 'w':0.0}

def extractPosition(position):
    pos = {}
    for d in ['x', 'y', 'z', 'a', 'b', 'c', 'u', 'v', 'w']:
        if position.HasField(d):
            pos[d] = position.__getattribute__(d)
    return pos

def mergePosition(self, posDict, name, proto, attr):
    if proto.HasField(attr):
        pos = extractPosition(proto.__getattribute__(attr))
        if posDict is None:
            dst = self.__getattribute__(name)
            dst.update(pos)
            return [name]
        else:
            dst = self.__getattribute__(posDict)
            dst[name].update(pos)
            return ["%s.%s" % (posDict, name)]
    return []

def mergeMember(self, member, proto, attr = None):
    if attr is None:
        attr = member
    if proto.HasField(attr):
        self.__setattr__(member, proto.__getattribute__(attr))
        return [member]
    return []

def mergeDictionary(self, member, name, proto, attr):
    if attr is None:
        attr = name
    if proto.HasField(attr):
        dst = self.__getattribute__(member)
        dst[name] = proto.__getattribute__(attr)
        return ["%s.%s" % (member, name)]
    return []

def returnAttribute(attr, path):
    if len(path) > 0:
        rest = path[1:]
        if type(attr) == dict:
            return returnAttribute(attr[path[0]], rest)
        if type(attr) == list:
            index = int(path[0])
            if hasattr(attr[0], 'index'):
                for element in attr:
                    if element.index == index:
                        return returnAttribute(element, rest)
                return attr[path[0]] # this will throw, we didn't find what we were looking for
            else:
                return returnAttribute(attr[index], rest)
        return returnAttribute(attr.__getattribute__(path[0]), rest)
    return attr

class MKAxisConfig(MKServiceContainer):
    def __init__(self, axis):
        super().__init__(True)
        self.index = axis.index
        self.limit = minmax(axis.min_position_limit, axis.max_position_limit)
        self.ferror = minmax(axis.min_ferror, axis.max_ferror)
        self.type = axis.axis_type
        self.maxV = axis.max_velocity
        self.maxA = axis.max_acceleration
        self.home_sequence = axis.home_sequence

    def merge(self, container):
        updated = []
        for axis in container.axis:
            if axis.index == self.index:
                updated += mergeMinMax(self.limit, 'limit', axis, 'position_limit')
                updated += mergeMinMax(self.ferror, 'ferror', axis, 'ferror')
                updated += mergeMember(self, 'type', axis, 'axis_type')
                updated += mergeMember(self, 'maxV', axis, 'max_velocity')
                updated += mergeMember(self, 'maxA', axis, 'max_acceleration')
                updated += mergeMember(self, 'home_sequence', axis)
        return ["axis.%d.%s" % (self.index, u) for u in updated]

class MKAxis(MKServiceContainer):
    def __init__(self, axis):
        super().__init__(True)
        self.index = axis.index
        self.enabled = axis.enabled
        self.fault = axis.fault
        self.ferror_current = axis.ferror_current
        self.ferror_highmark = axis.ferror_highmark
        self.homed = axis.homed
        self.homing = axis.homing
        self.limit = {}
        self.limit['soft'] = minmax(axis.min_soft_limit, axis.max_soft_limit)
        self.limit['hard'] = minmax(axis.min_hard_limit, axis.max_hard_limit)
        self.inpos = axis.inpos
        self.input = axis.input
        self.output = axis.output
        self.override_limits = axis.override_limits
        self.velocity = axis.velocity

    def merge(self, container):
        updated = []
        for axis in container.axis:
            if axis.index == self.index:
                updated += mergeMember(self, 'enabled', axis)
                updated += mergeMember(self, 'fault', axis)
                updated += mergeMember(self, 'ferror_current', axis)
                updated += mergeMember(self, 'ferror_highmark', axis)
                updated += mergeMember(self, 'homed', axis)
                updated += mergeMember(self, 'homing', axis)
                updated += mergeMember(self, 'inpos', axis)
                updated += mergeMember(self, 'input', axis)
                updated += mergeMember(self, 'output', axis)
                updated += mergeMember(self, 'override_limits', axis)
                updated += mergeMember(self, 'velocity', axis)
                updated += mergeMinMax(self.limit['soft'], 'limit.soft', axis, 'soft_limit')
                updated += mergeMinMax(self.limit['hard'], 'limit.hard', axis, 'hard_limit')
        return ["axis.%d.%s" % (self.index, u) for u in updated]


class MKServiceStatusHandler(MKServiceContainer):
    def __init__(self):
        super().__init__(False)
        self.fullUpdated = []

    def isValid(self):
        return self.valid

    def process(self, container):
        obj = self.handlerObject(container)
        updated = self.fullUpdated
        if container.type == MT_EMCSTAT_FULL_UPDATE:
            PathLog.debug("update full: %s" % self.topicName())
            updated = self.processFull(obj)
            self.fullUpdated = updated
            self.valid = True
        elif self.isValid():
            PathLog.debug("update incr: %s" % self.topicName())
            updated = self.processIncremental(obj)
        else:
            PathLog.debug("update ignd: %s" % self.topicName())
            updated = None
        if updated:
            self.notifyObservers(updated)

    def handlerObject(self, container):
        return container
    def topicName(self):
        return None

class MKServiceStatusHandlerConfig(MKServiceStatusHandler):

    def topicName(self):
        return 'status.config'

    def handlerObject(self, container):
        return container.emc_status_config

    def processFull(self, config):
        self.override = {}
        self.override['feed'] = minmax(config.min_feed_override, config.max_feed_override)
        self.override['spindle'] = minmax(config.min_spindle_override, config.max_spindle_override, config.default_spindle_speed)
        self.velocity = {}
        self.velocity['linear'] = minmax(config.min_linear_velocity, config.max_linear_velocity, config.default_linear_velocity)
        self.velocity['angular'] = minmax(config.min_linear_velocity, config.max_linear_velocity, config.default_angular_velocity)
        self.name = config.name
        self.units = {}
        self.units['time'] = config.time_units
        self.units['angular'] = config.angular_units
        self.units['linear'] = config.linear_units
        self.axis = [MKAxisConfig(axis) for axis in config.axis]
        self.axis_mask = config.axis_mask
        self.increments = config.increments.split(',')
        self.remote_path = config.remote_path

        return self.processIncremental(config)

    def processIncremental(self, config):
        updated = []
        updated += mergeMinMax(self.override['feed'], 'override.feed', config, 'feed_override')
        updated += mergeMinMax(self.override['spindle'], 'override.spindle', config, 'spindle_override', default='default_spindle_speed')
        updated += mergeMinMax(self.velocity['linear'], 'velocity.linear', config, 'linear_velocity', default='')
        updated += mergeMinMax(self.velocity['angular'], 'velocity.angular', config, 'angular_velocity', default='')
        updated += mergeMember(self, 'name', config)
        updated += mergeMember(self, 'axis_mask', config)
        updated += mergeMember(self, 'remote_path', config)
        updated += mergeDictionary(self, 'units', 'time', config, 'time_units')
        updated += mergeDictionary(self, 'units', 'angular', config, 'angular_units')
        updated += mergeDictionary(self, 'units', 'linear', config, 'linear_units')

        for axis in self.axis:
            updated += axis.merge(config)

        if config.HasField('increments'):
            self.increments = config.increments.split(',')
            updated.append('increments')

        return updated

class MKServiceStatusHandlerMotion(MKServiceStatusHandler):

    def topicName(self):
        return 'status.motion'

    def handlerObject(self, container):
        return container.emc_status_motion

    def processFull(self, motion):
        # processIncremental does everything we need, we just need to set up
        # the attributes so it can do its job
        self.adaptive_feed = motion.adaptive_feed_enabled
        self.ain =   [0.0] * len(motion.ain)
        self.aout =  [0.0] * len(motion.aout)
        self.din =   [0.0] * len(motion.din)
        self.dout =  [0.0] * len(motion.dout)
        self.limit = [0.0] * len(motion.limit)
        self.block_delete = motion.block_delete
        self.current_line = motion.current_line
        self.current_vel  = motion.current_vel
        self.delay_left = motion.delay_left
        self.distance_left = motion.distance_to_go
        self.enabled = motion.enabled
        self.feed = {}
        self.position = {}
        self.position['actual'] = defaultPosition()
        self.position['current'] = defaultPosition()
        self.position['joint']  = defaultPosition()
        self.position['joint_actual']  = defaultPosition()
        self.position['dtg']  = defaultPosition()
        self.g5x_index = motion.g5x_index
        self.offset = {}
        self.offset['g5x'] = defaultPosition()
        self.offset['g92'] = defaultPosition()
        self.axis = [MKAxis(axis) for axis in motion.axis]

        self.id = motion.id
        self.inpos = motion.inpos
        self.paused = motion.paused
        self.state = motion.state
        self.rotation_xy = motion.rotation_xy

        self.line = motion.motion_line
        self.type = motion.motion_type
        self.mode = motion.motion_mode

        self.probe = {}
        self.spindle = {}
        self.queue = {}
        self.max = {}

        return self.processIncremental(motion)

    def processIncremental(self, motion):
        updated = []

        def mergePins(dst, motion, pinsName):
            pins = motion.__getattribute__(pinsName)
            for p in pins:
                dst[p.index] = p.value
            return len(pins) > 0

        def updatePins(upd, dst, motion, pinsName):
            if mergePins(dst, motion, pinsName):
                upd.append(pinsName)

        updatePins(updated, self.ain,   motion, 'ain')
        updatePins(updated, self.aout,  motion, 'aout')
        updatePins(updated, self.din,   motion, 'din')
        updatePins(updated, self.dout,  motion, 'dout')
        updatePins(updated, self.limit, motion, 'limit')

        for axis in self.axis:
            updated += axis.merge(motion)

        updated += mergeMember(self, 'id', motion)
        updated += mergeMember(self, 'inpos', motion)
        updated += mergeMember(self, 'paused', motion)
        updated += mergeMember(self, 'state', motion)
        updated += mergeMember(self, 'rotation_xy', motion)
        updated += mergeMember(self, 'line', motion, 'motion_line')
        updated += mergeMember(self, 'type', motion, 'motion_type')
        updated += mergeMember(self, 'mode', motion, 'motion_mode')
        updated += mergeMember(self, 'g5x_index', motion)
        updated += mergeMember(self, 'block_delete', motion)
        updated += mergeMember(self, 'current_line', motion)
        updated += mergeMember(self, 'current_vel', motion)
        updated += mergeMember(self, 'delay_left', motion)
        updated += mergeMember(self, 'distance_left', motion, 'distance_to_go')
        updated += mergeMember(self, 'enabled', motion)
        updated += mergeMember(self, 'adaptive_feed', motion, 'adaptive_feed_enabled')

        updated += mergePosition(self, 'position', 'actual', motion, 'actual_position')
        updated += mergePosition(self, 'position', 'current', motion, 'position')
        updated += mergePosition(self, 'position', 'joint', motion, 'joint_position')
        updated += mergePosition(self, 'position', 'joint_actual', motion, 'joint_actual_position')
        updated += mergePosition(self, 'position', 'dtg', motion, 'dtg')
        updated += mergePosition(self, 'offset', 'g5x', motion, 'g5x_offset')
        updated += mergePosition(self, 'offset', 'g92', motion, 'g92_offset')

        updated += mergeDictionary(self, 'feed', 'hold', motion, 'feed_hold_enabled')
        updated += mergeDictionary(self, 'feed', 'override', motion, 'feed_override_enabled')
        updated += mergeDictionary(self, 'feed', 'rate', motion, 'feedrate')
        updated += mergeDictionary(self, 'feed', 'rapid', motion, 'rapidrate')
        updated += mergeDictionary(self, 'probe', 'active', motion, 'probing')
        updated += mergeDictionary(self, 'probe', 'tripped', motion, 'probe_tripped')
        updated += mergeDictionary(self, 'probe', 'value', motion, 'probe_val')
        updated += mergeDictionary(self, 'probe', 'position', motion, 'probed_position')
        updated += mergeDictionary(self, 'spindle', 'brake', motion, 'spindle_brake')
        updated += mergeDictionary(self, 'spindle', 'dir', motion, 'spindle_direction')
        updated += mergeDictionary(self, 'spindle', 'enabled', motion, 'spindle_enabled')
        updated += mergeDictionary(self, 'spindle', 'increasing', motion, 'spindle_increasing')
        updated += mergeDictionary(self, 'spindle', 'override', motion, 'spindle_override_enabled')
        updated += mergeDictionary(self, 'spindle', 'speed', motion, 'spindle_speed')
        updated += mergeDictionary(self, 'spindle', 'rate', motion, 'spindlerate')
        updated += mergeDictionary(self, 'queue', 'active', motion, 'active_queue')
        updated += mergeDictionary(self, 'queue', 'current', motion, 'queue')
        updated += mergeDictionary(self, 'queue', 'full', motion, 'queue_full')
        updated += mergeDictionary(self, 'max', 'velocity', motion, 'max_velocity')
        updated += mergeDictionary(self, 'max', 'acceleration', motion, 'max_acceleration')

        return updated

class MKTool:
    def __init__(self, tool):
        self.index = tool.index
        self.id = tool.id
        self.diameter = tool.diameter
        self.frontangle = tool.frontangle
        self.backangle = tool.backangle
        self.orientation = tool.orientation
        self.offset = defaultPosition()
        self.comment = ''
        self.pocket = tool.pocket

    def merge(self, container):
        updated = []
        for tool in container.tool_table:
            if tool.index == self.index:
                updated += mergeMember(self, 'id', tool)
                updated += mergeMember(self, 'diameter', tool)
                updated += mergeMember(self, 'frontangle', tool)
                updated += mergeMember(self, 'backangle', tool)
                updated += mergeMember(self, 'orientation', tool)
                updated += mergeMember(self, 'comment', tool)
                updated += mergeMember(self, 'pocket', tool)
                updated += mergePosition(self, None, 'offset', tool, 'offset')
        return ["tool.table.%d.%s" % (self.index, u) for u in updated]

class MKServiceStatusHandlerIO(MKServiceStatusHandler):
    def topicName(self):
        return 'status.io'

    def handlerObject(self, container):
        return container.emc_status_io

    def processFull(self, io):
        self.estop = io.estop
        self.flood = io.flood
        self.lube = io.lube
        self.lube_level = io.lube_level
        self.mist = io.mist
        self.tool = {}
        self.tool['offset'] = defaultPosition()
        self.tool['table'] = [MKTool(tool) for tool in io.tool_table]
        self.tool['nr'] = io.tool_in_spindle
        self.pocket_prepped = io.pocket_prepped

        return self.processIncremental(io)

    def processIncremental(self, io):
        updated = []

        updated += mergeMember(self, 'estop', io)
        updated += mergeMember(self, 'flood', io)
        updated += mergeMember(self, 'lube', io)
        updated += mergeMember(self, 'lube_level', io)
        updated += mergeMember(self, 'mist', io)
        updated += mergeMember(self, 'pocket_prepped', io)

        updated += mergePosition(self, 'tool', 'offset', io, 'tool_offset')
        updated += mergeDictionary(self, 'tool', 'nr', io, 'tool_in_spindle')

        for tool in self.tool['table']:
            updated += tool.merge(io)

        return updated


class MKServiceStatusHandlerTask(MKServiceStatusHandler):
    def topicName(self):
        return 'status.task'

    def handlerObject(self, container):
        return container.emc_status_task

    def processFull(self, task):
        self.serial = task.echo_serial_number
        self.state = task.exec_state
        self.file = task.file
        self.input_timeout = task.input_timeout
        self.optional_stop = task.optional_stop
        self.line = {}
        self.task = {}

        return self.processIncremental(task)

    def processIncremental(self, task):
        updated = []

        updated += mergeMember(self, 'serial', task, 'echo_serial_number')
        updated += mergeMember(self, 'state', task, 'exec_state')
        updated += mergeMember(self, 'file', task)
        updated += mergeMember(self, 'input_timeout', task)
        updated += mergeMember(self, 'optional_stop', task)
        updated += mergeDictionary(self, 'line', 'nr', task, 'read_line')
        updated += mergeDictionary(self, 'line', 'total', task, 'total_lines')
        updated += mergeDictionary(self, 'task', 'mode', task, 'task_mode')
        updated += mergeDictionary(self, 'task', 'state', task, 'task_state')
        updated += mergeDictionary(self, 'task', 'paused', task, 'task_paused')

        return updated


class MKServiceStatusHandlerInterpreter(MKServiceStatusHandler):
    def topicName(self):
        return 'status.interp'

    def handlerObject(self, container):
        return container.emc_status_interp

    def processFull(self, interp):
        self.command = interp.command
        self.state = interp.interp_state
        self.error = interp.interpreter_errcode
        self.units = interp.program_units
        self.gcodes = []
        self.mcodes = []
        self.settings = {}

        updated = self.processIncremental(interp)

        # make sure gcodes and mcodes are included although the list might be empty
        if not 'gcodes' in updated:
            updated.append('gcodes')
        if not 'mcodes' in updated:
            updated.append('mcodes')

        return updated

    def processIncremental(self, interp):
        updated = []

        updated += mergeMember(self, 'command', interp)
        updated += mergeMember(self, 'state', interp, 'interp_state')
        updated += mergeMember(self, 'error', interp, 'interpreter_errcode')
        updated += mergeMember(self, 'units', interp, 'program_units')

        gcodes = len(self.gcodes)
        self.gcodes = [(code.index, code.value) for code in interp.gcodes]
        if self.gcodes or gcodes > 0:
            updated.append('gcodes')
        mcodes = len(self.mcodes)
        self.mcodes = [(code.index, code.value) for code in interp.mcodes]
        if self.mcodes or mcodes > 0:
            updated.append('mcodes')

        for setting in interp.settings:
            if setting.index == 0:
                self.settings['sequence'] = setting.value
                updated.append('settings.sequence')
            if setting.index == 1:
                self.settings['feed'] = setting.value
                updated.append('settings.feed')
            if setting.index == 2:
                self.settings['velocity'] = setting.value
                updated.append('settings.velocity')

        return updated


class MKServiceStatus(MKServiceSubscribe):
    '''Gets and displayes the emc status'''

    def __init__(self, context, name, properties):
        MKServiceSubscribe.__init__(self, context, name, properties)
        self.handler = {
                'config': MKServiceStatusHandlerConfig(),
                'interp': MKServiceStatusHandlerInterpreter(),
                'io':     MKServiceStatusHandlerIO(),
                'motion': MKServiceStatusHandlerMotion(),
                'task':   MKServiceStatusHandlerTask()
                }
        self.pingme = []

    def topicNames(self):
        return ['motion', 'config', 'io', 'task', 'interp']

    def __getitem__(self, index):
        path = index.split('.') if type(index) == str else index
        if len(path) > 1:
            return self.handler[path[0]][path[1:]]
        return self.handler[path[0]]

    def isValid(self, topics=None):
        if topics is None:
            topics = self.topicNames()
        for topic in topics:
            handler = self.handler.get(topic)
            if handler is None or not handler.isValid():
                return False
        return True

    def process(self, container):
        if container.HasField('emc_status_config'):
            self.handler['config'].process(container)
        elif container.HasField('emc_status_interp'):
            self.handler['interp'].process(container)
        elif container.HasField('emc_status_io'):
            self.handler['io'].process(container)
        elif container.HasField('emc_status_motion'):
            self.handler['motion'].process(container)
        elif container.HasField('emc_status_task'):
            self.handler['task'].process(container)
        else:
            PathLog.notice("status[%s]: %s" % (container.type, [s[0].name for s in container.ListFields()]))

    def ping(self):
        for observer in self.pingme:
            observer.ping()

    def attach(self, observer, topicNames=None):
        if topicNames is None:
            topicNames = self.topicNames()
        for t in topicNames:
            handler = self.handler.get(t)
            if not handler is None:
                handler.attach(observer)
        if hasattr(observer, 'ping'):
            self.pingme.append(observer)

    def detach(self, observer, topicNames=None):
        if topicNames is None:
            topicNames = self.topicNames()
        for t in topicNames:
            handler = self.handler.get(t)
            if not handler is None:
                handler.detach(observer)

        self.pingme = [o for o in self.pingme if o != observer]
