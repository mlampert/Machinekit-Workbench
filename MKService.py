import zmq

from MKObserverable import *

class MKService(MKObserverable):
    '''The base class of all services'''
    def __init__(self, name, properties):
        super().__init__()

        self.service = properties[b'service']
        self.uuid    = properties[b'uuid']
        self.dsn     = properties[b'dsn']
        self.name    = self.service.decode()
        self.serviceName = name
        self.quit = False

    def setTermination(self):
        self.quit = True

    def wantsTermination(self):
        return self.quit

    def receiveMessage(self):
        # dealer-router just return the message
        # publish-subscribe also provide the topic
        return self.socket.recv_multipart()[-1]

    def process(self, container):
        pass

    def ping(self):
        pass


class MKServiceSubscribe(MKService):
    '''The base class for publish/subscribe based services'''
    def __init__(self, context, name, properties):
        MKService.__init__(self, name, properties)
        self.socket = context.socket(zmq.SUB)
        subs = self.topicNames()
        if not subs:
            subs = ['']
        for sub in subs:
            self.socket.setsockopt(zmq.SUBSCRIBE, sub.encode())
        self.socket.connect(self.dsn)

    def topicNames(self):
        pass
