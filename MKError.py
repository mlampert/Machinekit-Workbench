import enum

class MKErrorLevel(enum.Enum):
    Error   = 0
    Text    = 1
    Display = 2

class MKError(object):
    def __init__(self, lvl, msg):
        self.lvl = lvl
        self.msg = msg

    def level(self):
        return self.lvl

    def messages(self):
        return self.msg

    def isError(self):
        return self.lvl == MKErrorLevel.Error
    def isText(self):
        return self.lvl == MKErrorLevel.Text
    def isDisplay(self):
        return self.lvl == MKErrorLevel.Display

    def origin(self):
        pass

class MKErrorNml(MKError):
    def origin(self):
        return 'NML'

class MKErrorOperator(MKError):
    def origin(self):
        return 'OP'

