import linuxcnc as mk


class Machinekit(object):

    def __init__(self):
        self.cmd = mk.command()
        self.err = mk.error_channel()
        self.stat = mk.stat()

    def turnOn(self):
        self.update()
        if self.setMode(mk.MODE_MANUAL):
            self.setState(mk.STATE_ESTOP_RESET)
            self.setState(mk.STATE_ON)
            return True
        return False

    def turnOff(self):
        self.update()
        if self.setMode(mk.MODE_MANUAL):
            self.setState(mk.STATE_OFF)
            return True
        return False

    def isOn(self, check=True):
        if check:
            self.update()
        return self.stat.enabled and not self.stat.estop

    def isEstop(self, check=True):
        if check:
            self.update()
        return self.stat.estop

    def isHomed(self, check=True):
        if check:
            self.update()
        for i in range(3):
            if self.stat.axis[i]['homed'] == 0:
                return False
        return True

    def isInterpreterRunning(self):
        return self.isModeAuto() and not self.isInterpreterIdle()

    def isModeAuto(self):
        return self.stat.task_mode == mk.MODE_AUTO
    def isModeManual(self):
        return self.stat.task_mode == mk.MODE_MANUAL
    def isModeMDI(self):
        return self.stat.task_mode == mk.MODE_MDI

    def isInterpreterIdle(self):
        return self.stat.interp_state == mk.INTERP_IDLE


    def waitComplete(self):
        try:
            while self.cmd.wait_complete(.1) == -1:
                pass
            return True
        except KeyboardInterrupt:
            pass
        return False

    def setMode(self, mode):
        if self.stat.task_mode != mode:
            if self.isInterpreterRunning():
                return False
            self.cmd.mode(mode)
            return self.waitComplete()
        return True

    def setState(self, state):
        if self.stat.task_mode != state:
            self.cmd.state(state)
            return self.waitComplete()
        return False

    def homeAxis(self, axis=-1):
        if self.setMode(mk.MODE_MANUAL):
            self.cmd.home(axis)
            return self.waitComplete()
        return False


    def mdi(self, cmd, wait=True):
        if self.setMode(mk.MODE_MDI):
            self.cmd.mdi(cmd)
            if wait:
                return self.waitComplete()
        return False

    def pos(self):
        self.update()
        return self.stat.position

    def offset(self):
        return self.stat.g5x_offset

    def error(self):
        return self.err.poll()

    def update(self):
        self.stat.poll()


    def jogStop(self, axis, wait=True):
        self.cmd.jog(mk.JOG_STOP, axis)
        if wait:
            if self.waitComplete():
                return True
            self.jogStop(axis)
        return False

    def jogContinuous(self, axis, speed=1):
        self.cmd.jog(mk.JOG_CONTINUOUS, axis, speed)
        return True

    def jogIncrement(self, axis, speed=1, inc=1, wait=True):
        self.cmd.jog(mk.JOG_INCREMENT, axis, speed, inc)
        if wait:
            if self.waitComplete():
                return True
            self.jogStop(axis)
        return False

    def isComplete(self):
        self.update()
        return self.stat.state == mk.RCS_DONE or self.stat.state == mk.RCS_ERROR and self.stat.inpos == 1

