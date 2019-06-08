#!/usr/bin/python

import itertools
import machinetalk.protobuf.types_pb2   as TYPES
import threading
import uuid
import zmq

from MKCommand import *
from MKService import *

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
        self.observers = []

    def attach(self, observer):
        if not observer in self.observers:
            self.observers.append(observer)

    def detach(self, observer):
        self.observers = [o for o in self.observers if o != observer]

    def newTicket(self):
        with self.locked:
            return next(self.commandID)

    def sendCommand(self, msg):
        ticket = self.newTicket()
        msg.msg.ticket = ticket
        buf = msg.serializeToString()
        self.outstandingMsgs[ticket] = msg
        #print("add [%d]" % (ticket))
        msg.msgSent()
        self.socket.send(buf)
        if not msg.expectsResponses():
            msg.msgCompleted()
            self.msgChanged(msg)

    def msgChanged(self, msg):
        for observer in self.observers:
            observer.changed(self, msg)
        if msg.isCompleted():
            #print("del [%d]: " % (msg.msg.ticket, msg))
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
