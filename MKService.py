# Base classes for MK services implementing the basic interface
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
        '''Sets the receiver to be terminated - most likely the remote endpoint went away.'''
        self.quit = True

    def wantsTermination(self):
        '''Return true if this service has terminated and the receiver is no longer
        of any use.'''
        return self.quit

    def process(self, container):
        '''Called by the framework when a protobuf container is received from the
        MK's service endpoint to be processed by the receiver.
        Must be overwritten by subclasses.'''
        pass

    def ping(self):
        '''Periodically alled by the framework regardless of any messages being
        received for the receiver. Can be used for timed tasks and housekeeping
        functions.
        Can be overwritten by subclasses.'''
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
        '''Return a list of topicNames this service wants to subscribe to.
        Must be overwritten by subclasses.'''
        pass
