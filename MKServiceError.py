import machinetalk.protobuf.types_pb2 as TYPES

from MKError   import *
from MKService import *

class MKServiceError(MKServiceSubscribe):
    '''Gets and displays the emc status'''

    def __init__(self, context, name, properties):
        MKServiceSubscribe.__init__(self, context, name, properties)
        self.observers = []

    def topicNames(self):
        return ['error', 'text', 'display']

    def topicName(self):
        return 'error'

    def process(self, container):
        msg = None
        if container.type == TYPES.MT_EMC_OPERATOR_ERROR:
            msg = MKErrorOperator(MKErrorLevel.Error, container.note)
        if container.type == TYPES.MT_EMC_OPERATOR_TEXT:
            msg = MKErrorOperator(MKErrorLevel.Text, container.note)
        if container.type == TYPES.MT_EMC_OPERATOR_DISPLAY:
            msg = MKErrorOperator(MKErrorLevel.Display, container.note)

        if container.type == TYPES.MT_EMC_NML_ERROR:
            msg = MKErrorNml(MKErrorLevel.Error, container.note)
        if container.type == TYPES.MT_EMC_NML_TEXT:
            msg = MKErrorNml(MKErrorLevel.Text, container.note)
        if container.type == TYPES.MT_EMC_NML_DISPLAY:
            msg = MKErrorNml(MKErrorLevel.Display, container.note)

        if msg is None:
            print("error unknown: %s" % container)
        else:
            for observer in self.observers:
                observer.changed(self, msg)

    def attach(self, observer, topic=None):
        self.observers.append(observer)

    def detach(self, observer, topic=None):
        self.objservers = [o for o in self.observers if o != observer]
