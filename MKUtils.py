# some helper classes which are used in multiple places
import MKCommand
import machinetalk.protobuf.status_pb2 as STATUS

def _taskMode(service, mode, force):
    '''internal - do not use'''
    m = service['task.task.mode']
    if m is None:
        m = service['status.task.task.mode'] 
    if m != mode or force:
        return [MKCommand.MKCommandTaskSetMode(mode)]
    return []

def taskModeAuto(service, force=False):
    '''taskModeAuto(service, force=False) ... return a list of commands required to switch to AUTO mode.'''
    return _taskMode(service, STATUS.EMC_TASK_MODE_AUTO, force)

def taskModeMDI(service, force=False):
    '''taskModeMDI(service, force=False) ... return a list of commands required to switch to MDI mode.'''
    return _taskMode(service, STATUS.EMC_TASK_MODE_MDI, force)

def taskModeManual(service, force=False):
    '''taskModeManual(service, force=False) ... return a list of commands required to switch to MANUAL mode.'''
    return _taskMode(service, STATUS.EMC_TASK_MODE_MANUAL, force)

def pathSignature(path):
    '''Return a hash to identify a given Path. This is used to determine if a loaded Path in MK is still
    up to date with the Job in FC.'''
    signature = 0
    for cmd in path.Commands:
        for c in cmd.toGCode():
            signature += ord(c)
    return signature
