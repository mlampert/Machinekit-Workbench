import itertools
import machinetalk.protobuf.object_pb2 as OBJECT
import machinetalk.protobuf.types_pb2 as TYPES
import threading
import uuid
import zmq

from MKCommand import *
from MKError   import *
from MKService import *

def pinValueBit(container):
    return container.halbit
def pinValueS32(container):
    return container.hals32

PinValue = {
        TYPES.ValueType.Value('HAL_BIT') : pinValueBit,
        TYPES.ValueType.Value('HAL_S32') : pinValueS32,
        '' : None
        }

class Pin(object):
    def __init__(self, container):
        self.name = container.name.split('.')[-1]
        self.handle = container.handle
        self.type = container.type
        self.dir = container.dir
        # make sure type is set before calling setValue()
        self.setValue(container)

        #print("%s[%d]: %s" % (self.name, self.handle, self.value))

    def setValue(self, container):
        self.value = PinValue[self.type](container)

class ComponentManualToolChange(object):
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
        pin = self.pinID.get(container.handle)
        if pin:
            pin.setValue(container)
            return True
        return False

    def getPin(self, name):
        return self.pinName.get(name)

    def pinValue(self, name, default):
        pin = self.pinName.get(name)
        if pin:
            return pin.value
        return default
    
    def changeTool(self):
        return self.pinValue('change', False) and not self.pinValue('changed', False)

    def toolChanged(self):
        return not self.pinValue('change', False) and self.pinValue('changed', False)

    def toolNumber(self):
        return self.pinValue('number', 0)

class MKServiceHalStatus(MKServiceSubscribe):
    '''Gets and displayes the emc status'''

    def __init__(self, context, name, properties):
        MKServiceSubscribe.__init__(self, context, name, properties)
        self.toolChange = None

    def topicNames(self):
        # the simplest way to figure out if there is a manual tool change is to
        # subscribe to it - there will be an error if it doesn't exist
        return ['hal_manualtoolchange']

    def topicName(self):
        return 'halrcomp'

    def process(self, container):
        #print(container)
        if container.type ==  TYPES.MT_HALRCOMP_ERROR:
            # this will be the last time the service sends a message
            print("ERROR: %s" % container.note);
        elif container.type == TYPES.MT_HALRCOMP_FULL_UPDATE:
            for comp in container.comp:
                if comp.name == 'hal_manualtoolchange':
                    print('manual tool change detected')
                    self.toolChange = ComponentManualToolChange(comp)
        elif container.type == TYPES.MT_HALRCOMP_INCREMENTAL_UPDATE and self.toolChange:
            for pin in container.pin:
                if not self.toolChange.updatePin(pin):
                    #print(pin)
                    pass
        else:
            print(container)

        if self.toolChange:
            self.notifyObservers(self.toolChange)


    def toolChanged(self, service, value):
        pin = self.toolChange.getPin('changed')

        p = OBJECT.Pin()
        p.handle = pin.handle
        p.type   = pin.type
        p.halbit = value

        cmd = MKCommand(TYPES.MT_HALRCOMP_SET)
        cmd.msg.pin.extend([p])

        service.sendCommand(cmd)

class MKServiceHalCommand(MKService):
    def __init__(self, context, name, properties):
        MKService.__init__(self, name, properties)
        self.identity = uuid.uuid1()
        self.socket = context.socket(zmq.DEALER)
        self.socket.identity = str(self.identity).encode()
        self.socket.connect(self.dsn)
        self.commandID = itertools.count()
        self.locked = threading.Lock()

    def newTicket(self):
        with self.locked:
            return next(self.commandID)

    def sendCommand(self, msg):
        ticket = self.newTicket()
        msg.msg.ticket = ticket
        msg.msg.serial = ticket
        buf = msg.serializeToString()
        msg.msgSent()
        self.socket.send(buf)

    def process(self, container):
        print(container)
