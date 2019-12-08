# machinekit-local
These are scripts that can be copied onto the machine running Machinekit.

* `fc_manualtoolchange.hal` ... hal component to be used if tool change is to be acknowledged through the FC ui
* `rest-services`           ... a python http server providing a GET interface for all local haltalk services
* `rest-services-watch`     ... a python script to monitor the services published by `rest-services`
                                This is used as a debugging tool on the box which runs FC to verify which services
                                are published by the MK instance
* `machinekit.service`      ... `systemd` definition to kick off `rest-services`
* `pyremote`                ... a rudimentary interface for a pendant
* `jog.py`                  ... local interface to jog around and monitor position
* `mkshell.py`              ... beginning of a local command interface - poc

If you don't have an ATC and you want to do manual tool changes in FC similar to what is provided by Axis you should
use `fc_manualtoolchange.hal` in your `.ini` file. Whenever a TC is required FC will bring up a dialog box for you to
acknowledge that the tool has been inserted.

Copy `machinekit.service` to `/etc/systemd/system` and call
  `sudo systemctl daemon-reload`
  `sudo systemctl start machinekit.service`
  `sudo systemctl enable machinekit.service`
This should get the http service registry started on reboot so it doesn't have to be included in any of the HAL files.
Note that `rest-services` provides a plain text door for anybody with access to the box to the specific Machinekit
ports. If you subscribe to the _obfuscation is a form of security_ mantra than you should probably not use this it.

`pyremote` is intended for `loadusr` within a hal script (assuming they are somewhere in `PATH`). - highly
experimenta at this point

