import machinetalk.protobuf.types_pb2 as TYPES

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

        print("%s[%d]: %s" % (self.name, self.handle, self.value))

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

    def pinValue(self, name, default):
        pin = self.pinName.get(name)
        if pin:
            return pin.value
        return default
    
    def changeTool(self):
        print("changeTool: %s/%s" % (self.pinValue('change', False), self.pinValue('changed', False)))
        return self.pinValue('change', False) and not self.pinValue('changed', False)

    def toolNumber(self):
        return self.pinValue('number', 0)

class MKServiceHal(MKServiceSubscribe):
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
        if container.type ==  TYPES.MT_HALRCOMP_ERROR:
            # this will be the last time the service sends a message
            print("ERROR: %s" % container.note);
        elif container.type == TYPES.MT_HALRCOMP_FULL_UPDATE:
            for comp in container.comp:
                if comp.name == 'hal_manualtoolchange':
                    print('got tool change')
                    self.toolChange = ComponentManualToolChange(comp)
        elif container.type == TYPES.MT_HALRCOMP_INCREMENTAL_UPDATE and self.toolChange:
            for pin in container.pin:
                if not self.toolChange.updatePin(pin):
                    print(pin)
        else:
            print(container)

        if self.toolChange:
            self.notifyObservers(self.toolChange)

