# Basic logging implementation.

import os
import traceback

class Level:
    ERROR   = 0
    WARNING = 1
    NOTICE  = 2
    INFO    = 3
    DEBUG   = 4

_Level = {}

def thisModule():
    return _caller()[0]

def _caller():
    filename, line, func, text = traceback.extract_stack(limit=3)[0]
    return os.path.splitext(os.path.basename(filename))[0], line, func

def setLevel(level, module):
    _Level[module] = level

def debug(msg):
    _log(Level.DEBUG, _caller(), msg)
def info(msg):
    _log(Level.INFO, _caller(), msg)
def notice(msg):
    _log(Level.NOTICE, _caller(), msg)
def warning(msg):
    _log(Level.WARNING, _caller(), msg)
def error(msg):
    _log(Level.ERROR, _caller(), msg)

def _log(level, caller, msg):
    if level <= _Level.get(caller[0], Level.NOTICE):
        print("%s: %s" % (caller[0], msg))

