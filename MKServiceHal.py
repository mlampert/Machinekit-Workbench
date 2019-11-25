# Classes to directly interact with the MK HAL layer.

import MKLog
import itertools
import machinetalk.protobuf.object_pb2 as OBJECT
import machinetalk.protobuf.types_pb2 as TYPES
import threading
import uuid
import zmq

from MKCommand import *
from MKError   import *
from MKService import *

MKLog.setLevel(MKLog.Level.INFO, MKLog.thisModule())

def pinValueBit(container):
    '''Helper function to get the bool value of a pin.'''
    return container.halbit
def pinValueS32(container):
    '''Helper function to get the int32_t value of a pin.'''
    return container.hals32

PinValue = {
        TYPES.HAL_BIT : pinValueBit,
        TYPES.HAL_S32 : pinValueS32,
        '' : None
        }

class Pin(object):
    '''Helper class represing a specific pin in HAL.'''
    def __init__(self, container):
        self.name = container.name.split('.')[-1]
        self.handle = container.handle
        self.type = container.type
        self.dir = container.dir
        # make sure type is set before calling setValue()
        self.setValue(container)

        #print("%s[%d]: %s" % (self.name, self.handle, self.value))

    def setValue(self, container):
        '''setValue(container) ... Update receivers value from the container.'''
        self.value = PinValue[self.type](container)

class ComponentManualToolChange(object):
    '''Companion class to fc_manualtoolchange.hal
    Should the FC manual tool change be loaded in HAL this class will interact with it
    and prompt the user for the tool change - and then update HAL to either complete the
    tool change or abort task execution.'''

    def __init__(self, container):
        self.name = container.name
        self.handle = container.comp_id
        self.type = container.type
        self.pinID = {}
        self.pinName = {}
        for pin in container.pin:
            p = Pin(pin)
            self.pinID[p.handle] = p
            self.pinName[p.name] = p

    def updatePin(self, container):
        '''Called by the framework to update the value of a pin.
        Returns True if the value was updated.'''
        pin = self.pinID.get(container.handle)
        if pin:
            pin.setValue(container)
            return True
        return False

    def getPin(self, name):
        '''Return the FC manual tool change pin with the given name.'''
        return self.pinName.get(name)

    def pinValue(self, name, default):
        '''Return the value of the given pin. If it can't be found return default.'''
        pin = self.pinName.get(name)
        if pin:
            return pin.value
        return default
    
    def changeTool(self):
        '''Return True if a tool change is required.'''
        return self.pinValue('change', False) and not self.pinValue('changed', False)

    def toolChanged(self):
        '''Return True if the tool change is completed.'''
        return not self.pinValue('change', False) and self.pinValue('changed', False)

    def toolNumber(self):
        '''Return the number of the tool in the spindle (0 means no tool).'''
        return self.pinValue('number', 0)

class MKServiceHalStatus(MKServiceSubscribe):
    '''Gets and displayes the emc status'''

    def __init__(self, context, name, properties):
        MKServiceSubscribe.__init__(self, context, name, properties)
        self.toolChange = None

    def topicNames(self):
        # the simplest way to figure out if there is a manual tool change is to
        # subscribe to it - there will be an error if it doesn't exist
        return ['fc_manualtoolchange']

    def topicName(self):
        return 'halrcomp'

    def process(self, container):
        '''Called by the framework when a proto buf is received from MK's 'halrcomp' service.'''
        if container.type ==  TYPES.MT_HALRCOMP_ERROR:
            for note in container.note:
                if 'fc_manualtoolchange' in note and 'does not exist' in note:
                    # this will be the last time the service sends a message
                    MKLog.info('no manual tool change')
                else:
                    MKLog.error(note)

        elif container.type == TYPES.MT_HALRCOMP_FULL_UPDATE:
            for comp in container.comp:
                if comp.name == 'fc_manualtoolchange':
                    MKLog.info('manual tool change detected')
                    self.toolChange = ComponentManualToolChange(comp)
        elif container.type == TYPES.MT_HALRCOMP_INCREMENTAL_UPDATE and self.toolChange:
            for pin in container.pin:
                if not self.toolChange.updatePin(pin):
                    #print(pin)
                    pass
        else:
            print('halrcomp', container)

        if self.toolChange:
            self.notifyObservers(self.toolChange)


    def toolChanged(self, service, value):
        '''Call once the tool chanage has been confirmed.'''
        pin = self.toolChange.getPin('changed')

        p = OBJECT.Pin()
        p.handle = pin.handle
        p.type   = pin.type
        p.halbit = value

        cmd = MKCommand(TYPES.MT_HALRCOMP_SET)
        cmd.msg.pin.extend([p])

        service.sendCommand(cmd)

def protoDump(obj, prefix=''):
    '''Debugging function to print an entire proto buf without knowing anything about its structure.'''
    if not prefix:
        prefix = obj.DESCRIPTOR.name
    for descriptor in obj.DESCRIPTOR.fields:
        value = getattr(obj, descriptor.name)
        if descriptor.type == descriptor.TYPE_MESSAGE:
            pfix = "%s.%s" % (prefix, descriptor.name)
            if descriptor.label == descriptor.LABEL_REPEATED:
                for i, v in enumerate(value):
                    protoDump(v, "%s.%d.%s" % (pfix, i, v.name))
            else:
                protoDump(value, pfix)
        elif descriptor.type == descriptor.TYPE_ENUM:
            print("%s.%s: %s (%s.%s)" % (prefix, descriptor.name, value, descriptor.enum_type.name, descriptor.enum_type.values_by_number[value].name))
        else:
            print("%s.%s: %s" % (prefix, descriptor.name, value))

class MKServiceHalCommand(MKService):
    '''Class to interact directly with MK's HAL service.'''

    def __init__(self, context, name, properties):
        MKService.__init__(self, name, properties)
        self.identity = uuid.uuid1()
        self.socket = context.socket(zmq.DEALER)
        self.socket.identity = str(self.identity).encode()
        self.socket.connect(self.dsn)
        self.commandID = itertools.count()
        self.locked = threading.Lock()

        # You wanna know what's going on?
        # components? signals? anything else?
        #self.sendCommand(MKCommand(TYPES.MT_HALRCOMMAND_DESCRIBE))

    def newTicket(self):
        '''Return a unique value to be used as the ticket so responses can be matched to their request.'''
        with self.locked:
            return next(self.commandID)

    def sendCommand(self, msg):
        '''Send the given message the MK's HAL service.'''
        ticket = self.newTicket()
        msg.msg.ticket = ticket
        msg.msg.serial = ticket
        buf = msg.serializeToString()
        msg.msgSent()
        self.socket.send(buf)

    def process(self, container):
        '''Called by the framework when MK's HAL service sends a response message to a command.'''
        if container.type == TYPES.MT_HALRCOMMAND_DESCRIPTION:
            protoDump(container)
        else:
            print('halrcmd', container)

