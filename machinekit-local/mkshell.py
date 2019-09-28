#!/usr/bin/python
# https://gist.github.com/mhaberler/ba6030d75a67c113907b

import argparse
import cmd
import linuxcnc as mk
import machinekit

class MkShell(cmd.Cmd):

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.mk = machinekit.Machinekit()

    def do_on(self, arg, opts=None):
        '''Turn machine on'''
        self.mk.turnOn()

    def do_off(self, arg, opts=None):
        '''Turn machine off'''
        self.mk.turnOff()

    def do_mdi(self, arg, opts=None):
        '''Execute MDI command'''
        self.mk.mdi(''.join(arg))

    def do_home(self, arg, opts=None):
        '''Home axis, or all axis if none is given'''
        self.mk.homeAxis(-1)

    def do_pos(self, arg, opts=None):
        '''Print current position'''
        p = self.mk.pos()
        print("(%.2f, %.2f, %.2f)" % (p[0], p[1], p[2]))

    def do_EOF(self, arg, opts=None):
        '''Stop using the shell'''
        return True

parser = argparse.ArgumentParser()
parser.add_argument('cmd', help='Command to execute, if empty enable interactive mode', nargs='*')
parser.add_argument('--interactive', help='Enable interactive mode even when cmds specified', action='store_true')
args = parser.parse_args()

app = MkShell()

for cmd in args.cmd:
    app.onecmd(cmd)

if not args.cmd or args.interactive:
    app.cmdloop()
