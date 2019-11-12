# MKError holds the classes used to represent errors and other notification messages from MK.

import enum

class MKErrorLevel(enum.Enum):
    '''Enumeration of the different types of messages MK can send to the UI.'''
    Error   = 0
    Text    = 1
    Display = 2

class MKError(object):
    '''Base class for all errors and notifications from MK.'''
    def __init__(self, lvl, msg):
        self.lvl = lvl
        self.msg = msg

    def level(self):
        '''Return the MKErrorLevel of all messages of this notification.'''
        return self.lvl

    def messages(self):
        '''Return a list of message strings.'''
        return self.msg

    def isError(self):
        '''Return True if receiver is an error message.'''
        return self.lvl == MKErrorLevel.Error
    def isText(self):
        '''Return True if receiver is a text message.'''
        return self.lvl == MKErrorLevel.Text
    def isDisplay(self):
        '''Return True if receiver is a display message.'''
        return self.lvl == MKErrorLevel.Display

    def origin(self):
        pass

class MKErrorNml(MKError):
    '''Class used for NML notifications from MK.'''
    def origin(self):
        return 'NML'

class MKErrorOperator(MKError):
    '''Class used for all notifications from MK which are considered operator errors.'''
    def origin(self):
        return 'OP'

