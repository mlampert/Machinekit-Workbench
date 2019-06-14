#!/usr/bin/python

import itertools
import machinetalk.protobuf.types_pb2   as TYPES
import threading
import uuid
import zmq

from MKCommand import *
from MKService import *

class MKCommandWaitUntil(object):
    def __init__(self, condition):
        self.condition = condition

    def resume(self):
        return self.condition()

class CommandSequence(object):
    def __init__(self, service, sequence):
        self.service = service
        self.sequence = sequence
        self.msgs = []
        self.wait = None

    def isActive(self):
        return len(self.sequence) != 0 or len(self.msgs) != 0 or not self.wait is None

    def start(self):
        self.sendBatch()

    def processCommand(self, msg):
        if msg.isCompleted() and msg in self.msgs:
            self.msgs.remove(msg)

    def sendBatch(self):
        if self.sequence:
            batch = self.sequence.pop(0)
            for command in batch:
                if type(command) == MKCommandWaitUntil:
                    self.wait = command
                else:
                    self.msgs.append(command)
                    self.service.sendCommand(command)

    def ping(self):
        if not self.msgs and ((self.wait is None) or self.wait.resume()):
            self.wait = None
            self.sendBatch()

class MKServiceCommand(MKService):
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
        return 'command'

    def newTicket(self):
        with self.locked:
            return next(self.commandID)

    def sendCommand(self, msg):
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

    def msgChanged(self, msg):
        for compound in self.compounds:
            compound.processCommand(msg)
        self.compounds = [compound for compound in self.compounds if compound.isActive()]

        self.notifyObservers(msg)

        if msg.isCompleted() and self.outstandingMsgs.get(msg.msg.ticket):
            #print("del [%d]: %s" % (msg.msg.ticket, msg))
            del self.outstandingMsgs[msg.msg.ticket]

    def process(self, container):
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

    def sendCommandSequence(self, sequence):
        command = CommandSequence(self, sequence)
        self.compounds.append(command)
        command.start()

    def sendCommands(self, commands):
        if 1 == len(commands):
            self.sendCommand(commands[0])
        else:
            self.sendCommandSequence([[command] for command in commands])

    def ping(self):
        for compound in self.compounds:
            compound.ping()
        self.compounds = [compound for compound in self.compounds if compound.isActive()]

