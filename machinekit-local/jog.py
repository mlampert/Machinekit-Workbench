#!/usr/bin/python
#
# ncurses interface for some basic machine operations
#  * power on/off
#  * home all axis
#  * jog around, incremental and continuous
#  * override jogging speed
#  * DRO

import curses
import linuxcnc
import machinekit
import os
import time


class Jog(object):
    CONTINUOUS = 0
    INCREMENT  = 1
    Increment  = [0.1, 1, 10, 100]
    AxisDef    = {
            'x' : [0, 'x', 'X'],
            'y' : [1, 'y', 'Y'],
            'z' : [2, 'z', 'Z'],
            }

    def __init__(self):
        self.mk = machinekit.Machinekit()
        self.jogX = 0
        self.jogY = 0
        self.jogZ = 0
        self.speed = 20
        self.increment = 1
        self.mode = self.CONTINUOUS
        self.cmds = []

    def setSpeed(self, speed):
        if self.speed != speed:
            self.speed = speed
            self.updateJog()

    def setIncrement(self, inc):
        if self.increment != inc:
            self.increment = inc

    def speedInc(self):
        self.speed = self.speed / 0.7

    def speedDec(self):
        self.speed = self.speed * 0.7

    def setMode(self, mode):
        if self.mode != mode:
            self.mode = mode
            self.updateJog()

    def updateJog(self):
        if self.mode == self.CONTINUOUS:
            self._updateJogAxis(0, self.jogX)
            self._updateJogAxis(1, self.jogY)
            self._updateJogAxis(2, self.jogZ)

    def _updateJogAxis(self, axis, val):
        if val < 0:
            val = -self.speed
        if val > 0:
            val = self.speed

        if val != 0:
            self.mk.jogContinuous(axis, val)
        else:
            self.mk.jogStop(axis, False)

        return val

    def stop(self):
        self.jogX = 0
        self.jogY = 0
        self.jogZ = 0
        self.mk.jogStop(0, False)
        self.mk.jogStop(1, False)
        self.mk.jogStop(2, False)
        self.mk.waitComplete()

    def jogAxis(self, axis, v, a, force):
        if a[1] == axis:
            if force or v != 1:
                self.mk.setMode(linuxcnc.MODE_MANUAL)
                if self.mode == self.CONTINUOUS:
                    self.mk.jogContinuous(a[0], self.speed)
                else:
                    self.mk.jogIncrement(a[0], self.speed, self.increment, False)
                v = 1
        elif a[2] == axis:
            if force or v != -1:
                self.mk.setMode(linuxcnc.MODE_MANUAL)
                if self.mode == self.CONTINUOUS:
                    self.mk.jogContinuous(a[0], -self.speed)
                else:
                    self.mk.jogIncrement(a[0], -self.speed, self.increment, False)
                v = -1
        elif v != 0:
            self.mk.setMode(linuxcnc.MODE_MANUAL)
            self.mk.jogStop(a[0], False)
            v = 0
        return v

    def jog(self, axis, force=False):
        self.jogX = self.jogAxis(axis, self.jogX, self.AxisDef['x'], force)
        self.jogY = self.jogAxis(axis, self.jogY, self.AxisDef['y'], force)
        self.jogZ = self.jogAxis(axis, self.jogZ, self.AxisDef['z'], force)

    def jogHome(self):
        self.mk.update()
        pos = self.mk.pos()
        # remember mode for restoring later and then set it to INCREMENT
        mode = self.mode
        self.mode = self.INCREMENT

        def jogHomeXY(s, p):
            s.mk.jogIncrement(0, s.speed, -p[0], False)
            s.mk.jogIncrement(1, s.speed, -p[1], False)

        if pos[2] < 0:
            self.mk.jogIncrement(2, self.speed, -pos[2], False)
            self.cmds.append(lambda s: jogHomeXY(s, pos))
        else:
            jogHomeXY(self, pos)
            self.cmds.append(lambda s: s.mk.jogIncrement(2, s.speed, -pos[2], False))
        self.cmds.append(lambda s: s.setMode(mode))

    def isComplete(self):
        if self.mode == self.INCREMENT or self.mk.isModeMDI():
            complete =  self.mk.isComplete()
            return complete
        return True

    def popCommand(self):
        if self.cmds:
            cmd = self.cmds[0]
            self.cmds = self.cmds[1:]
            return cmd
        return None

Key2Axis = {
        curses.KEY_RIGHT : 'x',
        curses.KEY_LEFT  : 'X',
        curses.KEY_UP    : 'y',
        curses.KEY_DOWN  : 'Y',
        curses.KEY_PPAGE : 'z',
        curses.KEY_NPAGE : 'Z',
        }

def printHelp(win):
    bottom = curses.LINES-1
    win.addstr(bottom - 1, 0, "c/i/m ... mode, +/- ... speed, 1-6 ... incr, o/O ... on/off, HOME ... home")
    win.addstr(bottom,     0, "cursor ... X/Y, page ... Z, 0 ... 0.0.0, r ... screen refresh")

Key2Command = {
        ord('+') : lambda j,w: Jog.speedInc(j),
        ord('-') : lambda j,w: Jog.speedDec(j),
        ord('c') : lambda j,w: Jog.setMode(j, Jog.CONTINUOUS),
        ord('i') : lambda j,w: Jog.setMode(j, Jog.INCREMENT),
        ord('m') : lambda j,w: Jog.setMode(j, Jog.CONTINUOUS if j.mode == Jog.INCREMENT else Jog.INCREMENT),
        ord('1') : lambda j,w: Jog.setIncrement(j, Jog.Increment[0]),
        ord('2') : lambda j,w: Jog.setIncrement(j, Jog.Increment[1]),
        ord('3') : lambda j,w: Jog.setIncrement(j, Jog.Increment[2]),
        ord('4') : lambda j,w: Jog.setIncrement(j, Jog.Increment[3]),
        ord('h') : lambda j,w: machinekit.Machinekit.homeAxis(j.mk),
        ord('O') : lambda j,w: machinekit.Machinekit.turnOff(j.mk),
        ord('o') : lambda j,w: machinekit.Machinekit.turnOn(j.mk),
        ord('0') : lambda j,w: Jog.jogHome(j),
        ord('r') : lambda j,w: w.clear(),
        ord('?') : lambda j,w: printHelp(w),
        }

progr = '-\\|/'

def printSettings(win, jog):
    win.addstr(0, 5, "Mode:  %c   Speed: %6.2f   Incr:  %6.2f      " % ('C' if jog.mode == Jog.CONTINUOUS else 'I', jog.speed, jog.increment))

def printDRO(win, mk, attr):
    p = mk.pos()
    win.addstr(1, 2, "X: %9.3f " % p[0], attr)
    win.addstr(2, 2, "Y: %9.3f " % p[1], attr)
    win.addstr(3, 2, "Z: %9.3f " % p[2], attr)

def main(win):
    jog = Jog()
    i = 0
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.halfdelay(2)
    curses.curs_set(0)
    win.clear()
    printSettings(win, jog)
    then = time.time()
    err = None
    inputBuffer = []
    dro = curses.newwin(5, 16, curses.LINES/2-3, curses.COLS/2-8)
    dro.border()
    #dro.addstr(0, 1, ' DRO ')
    while 1:
        try:
            ch = -1
            if jog.isComplete():
                cmd = jog.popCommand()
                if cmd:
                    cmd(jog)
                else:
                    if inputBuffer:
                        ch = inputBuffer[0]
                        inputBuffer = inputBuffer[1:]
                    else:
                        ch = win.getch()
                    axis = Key2Axis.get(ch)
                    jog.jog(axis, jog.mode == Jog.INCREMENT)
                    cmd = Key2Command.get(ch)
                    if cmd:
                        cmd(jog, win)
                        printSettings(win, jog)
                    if ord('q') == ch or ord('Q') == ch:
                        break
            else:
                ch = win.getch()
                cmd = Key2Command.get(ch)
                if cmd:
                    cmd(jog, win)
                    printSettings(win, jog)
                elif -1 != ch:
                    inputBuffer.append(ch)

            #if -1 != ch:
            #    win.addstr(0, 0, "%d" % ch)

            now = time.time()
            if True or (now - then) >= 0.1:
                i = (i + 1) % len(progr)
                #attr = curses.A_NORMAL if jog.mk.isOn() else curses.A_REVERSE
                if jog.mk.isOn():
                    if jog.mk.isHomed(False):
                        attr = curses.color_pair(1)
                    else:
                        attr = curses.color_pair(4)
                elif jog.mk.isEstop(False):
                    attr = curses.color_pair(3)
                else:
                    attr = curses.color_pair(2)
                win.addch(0, curses.COLS-1, progr[i])
                printDRO(dro, jog.mk, attr)
                win.refresh()
                dro.refresh()
                then = now

            e = jog.mk.error()
            if e:
                kind, msg = e
                if kind in [linuxcnc.NML_ERROR, linuxcnc.OPERATOR_ERROR]:
                    msg = "ERROR: %s" % msg
                else:
                    msg = "INFO: %s" % msg
                win.addstr(curses.LINES-2, 1, "%s %s" % (time.strftime('%H:%M:%S'), msg))
                err = now
            elif err and (now - err) > 10:
                win.move(curses.LINES-2, 1)
                win.clrtoeol()
                err = None


        except KeyboardInterrupt:
            jog.mk.update()
            if jog.mk.stat.task_mode == linuxcnc.MODE_MDI:
                jog.mk.cmd.abort()
            else:
                jog.stop()
            inputBuffer = []

curses.wrapper(main)
