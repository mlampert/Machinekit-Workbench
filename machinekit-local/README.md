# machinekit-local
These are scripts that can be copied onto the machine running Machinekit.

* fc_manualtoolchange.hal ... hal component to be used if tool change is to be acknowledged through the FC ui
* rest-services           ... a python http server providing a GET interface for all local haltalk services
* pyremote                ... a rudimentary interface for a pendant
* jog.py                  ... local interface to jog around and monitor position
* mkshell.py              ... beginning of a local command interface - poc

If you don't have an ATC and you want to do manual tool changes in FC similar to what is provided by Axis you should
use `fc_manualtoolchange.hal` in your `.ini` file. Whenever a TC is required FC will bring up a dialog box for you to
acknowledge that the tool has been inserted.

`rest-service` and `pyremote` are intended for `loadusr` within a hal script (assuming they are somewhere in `PATH`).

Note that `rest-services` provides a plain text door for anybody with access to the box to the specific Machinekit
ports. If you subscribe to the _obfuscation is a form of security_ mantra than you should probably not use this it.
