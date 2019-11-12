# Service implementation to interact with the MK service 'command'.
#
# This is the main interface to make MK do something. Most commands sent to MK
# will get a response in the form of status updates (typically two, one for
# executing and another one for its completion).
# However, the impact of most commands need to be observed by tracking the 'status'
# of MK.

import itertools
import machinetalk.protobuf.types_pb2   as TYPES
import threading
import uuid
import zmq

from MKCommand import *
from MKService import *

class MKCommandWaitUntil(object):
    '''Helper class to check if a certain condition has become true.'''
    def __init__(self, condition):
        self.condition = condition

    def resume(self):
        '''Return True if the initial condition is fulfilled.'''
        return self.condition()

class CommandSequence(object):
    '''Helper class to send a sequence of commands to MK.
    A squence is a list of command lists. All commands of an inner list are sent concurrenlty
    to MK without waiting for them to be processed and completed by MK.
    However, the next list of commands is not sent until all commands of the previous list have
    completed their execution.'''
    def __init__(self, service, sequence):
        self.service = service
        self.sequence = sequence
        self.msgs = []
        self.wait = None

    def isActive(self):
        '''Return True if the receiver has more commands to send or if some commands
        are still being processed by MK.'''
        return len(self.sequence) != 0 or len(self.msgs) != 0 or not self.wait is None

    def start(self):
        '''Initiate sending the first list of commands to MK.'''
        self.sendBatch()

    def processCommand(self, msg):
        '''This member is called by the framework whenever MK sends a response to a command.
        If the command is completed and the receiver is waiting for its completion the command
        is removed from the tracking.'''
        if msg.isCompleted() and msg in self.msgs:
            self.msgs.remove(msg)

    def sendBatch(self):
        '''Called by the framework to send the next available list of commands to MK and add them
        to the list of commands to be completed before the next batch can be sent.'''
        if self.sequence:
            batch = self.sequence.pop(0)
            for command in batch:
                if type(command) == MKCommandWaitUntil:
                    self.wait = command
                else:
                    self.msgs.append(command)
                    self.service.sendCommand(command)

    def ping(self):
        '''Periodically called by the framework - checks if the receiver is still waiting for
        the completion of any commands, and sends the next batch if that is not the case.'''
        if not self.msgs and ((self.wait is None) or self.wait.resume()):
            self.wait = None
            self.sendBatch()

class MKServiceCommand(MKService):
    '''Class to interact with the MK service 'command'.
    The receiver keeps track of the service's state and the completion status of any commands
    that have been sent to MK.'''

    def __init__(self, context, name, properties):
        MKService.__init__(self, name, properties)
        self.identity = uuid.uuid1()
        self.socket = context.socket(zmq.DEALER)
        self.socket.identity = str(self.identity).encode()
        self.socket.connect(self.dsn)
        self.commandID = itertools.count()
        self.locked = threading.Lock()
        self.outstandingMsgs = {}
        self.compounds = []

    def topicName(self):
        '''The service's name.'''
        return 'command'

    def newTicket(self):
        '''A ticket is the way of how a client connects MK's response message to a
        request. When sending a command to MK the ticket should be set to a unique
        value. MK willl set the same ticket number on all status updates for the
        command.'''
        with self.locked:
            return next(self.commandID)

    def msgChanged(self, msg):
        '''internal callback when the status of a tracked command has changed.'''
        for compound in self.compounds:
            compound.processCommand(msg)
        self.compounds = [compound for compound in self.compounds if compound.isActive()]

        self.notifyObservers(msg)

        if msg.isCompleted() and self.outstandingMsgs.get(msg.msg.ticket):
            #print("del [%d]: %s" % (msg.msg.ticket, msg))
            del self.outstandingMsgs[msg.msg.ticket]

    def process(self, container):
        '''process(container) ... called by the framework when a proto buf message from MK's
        command service was received.'''
        if container.type == TYPES.MT_ERROR:
            for msg in container.note:
                print("   ERROR: %s" % msg)
            print('')
            self.setTermination()
            return
                
        if container.HasField('reply_ticket'):
            msg = self.outstandingMsgs.get(container.reply_ticket)
            if msg:
                msg = self.outstandingMsgs[container.reply_ticket]
                if container.type == TYPES.MT_EMCCMD_EXECUTED:
                    msg.msgExecuted()
                if container.type == TYPES.MT_EMCCMD_COMPLETED:
                    msg.msgCompleted()
                self.msgChanged(msg)
            else:
                print("process(%s) - unknown ticket" % container)
        else:
            print("process(%s)" % container)

    def sendCommand(self, msg):
        '''Sends a command to MK.'''
        ticket = self.newTicket()
        msg.msg.ticket = ticket
        buf = msg.serializeToString()
        self.outstandingMsgs[ticket] = msg
        #print("add [%d]: %s" % (ticket, msg))
        msg.msgSent()
        self.socket.send(buf)
        if not msg.expectsResponses():
            msg.msgCompleted()
            self.msgChanged(msg)

    def sendCommands(self, commands):
        '''Sends a list of commands to MK - waiting for each commands completion before sending the next.'''
        if 1 == len(commands):
            self.sendCommand(commands[0])
        else:
            self.sendCommandSequence([[command] for command in commands])

    def sendCommandSequence(self, sequence):
        '''Send a list of command lists to MK.
        The outer list determines synchronisation points where the framework waits for the completion of
        all outstanding commands before sending the next commands to MK. The inner list are commands which
        are sent to MK in parallel.'''
        command = CommandSequence(self, sequence)
        self.compounds.append(command)
        command.start()

    def abortCommandSequence(self):
        '''Assuming there is a command sequence being processed this call will stop sending any more commands
        from those sequences to MK.'''
        self.compounds = []

    def ping(self):
        '''Periodically called by framework. Used to track the status of command sequences and trigger sending
        the next batch if appropriate.'''
        for compound in self.compounds:
            compound.ping()
        self.compounds = [compound for compound in self.compounds if compound.isActive()]

