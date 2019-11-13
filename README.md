# Machinekit-Workbench
FreeCAD workbench for Machinekit integration in Python 3 of an XYZ cnc.

At least that's what it's supposed to be once it grows up - which might take a bit of time.

There are currently 4 interfaces available:
* Hud     ... Head Up Display of coordinates and tool in the 3d view
* Jog     ... jogging and setting the coordinate offset
* Execute ... load, run/pause/stop Path Jobs in MK
* Combo   ... Combination of all of above interfaces + a Status interface

The workbench has preferences which allow some configuration - mostly of the Hud.

Having said all that the main purpose of the workbench is to amend the Path workbench toolbar with a Combo
command for each MK instance the workbench discovers. That way MK can be started directly from Path once the
Job is setup and all its operations are ready for processing.

The Machinekit workbench itself is mostly useful for development and debugging.

## Hud
The Hud is pretty straight forward and prints the coordinates (working and machine) in the 3d view and also
draws the tool in its current position. The color of the DRO and the tool is used to indicate if power is on,
all axes are homed and if the spindle is rotating or not. Check the preferences for details.

## Jog
The Jog dock widget provides an interface to jog the tool around and to set the offset of the coordinate system.
It's title inidcates the name of the MK instance it is connected to.

### DRO
The DRO displays the actual position of each axis. The current position can be set by changing the value in the
spinbox and activating it by pressing the corresponding axis button.

Shortcut buttons are available to set the coordinate(s) to `0`

### Jog
The `Z` and `XY` buttons jog the tool to the `0` position of the respective axes. If `Continuous` is selected
jogging continues for as long as a button is pressed, otherwise the fixed distance of the combo box is jogged
in the button's direction.

While `Jog To` is pressed the user can click a point in the 3d view and MK will jog the tool to that location.
Initially only the `XY` axes are modified - however a second click on the same location also jogs the `Z` axis.

## Execute
In order to load a Job into MK one selects the Job in the Tree and then presses `Load`. Once a job is loaded
the title of the dock widget is changed to the label of the Job and the `Run` and `Step` buttons are enabled.

The bottom slider and spinbox represent the feed override value. The feed rate is changed once the slider is
released or, if the value is entered directly into the spinbox, editing is finished. Note that only the feed
rate is scaled and not the rapid rate. It is assumed that rapid moves are always performed at the max speed.

At the very bottom is a status bar which is currently used for debugging - the most useful info is displayed
at the end where the current line number and total number of lines are displayed.

## Combo
The Combo is used to integrate all views into a single tab widget for one MK instance. They are dynamically
created as MK instances are discovered and added to the Path workbench (assuming this is enabled in the
preferences).

### Status
A Status tab is added to the Combo dock in order to display and modify some status settings. Currently E-Stop,
Power and Homing are available.


## MDI
Issuing MDI commands is possible by accessing the Machinekit object and interacting with directly in the
Python console. Use `machinekit.Instances()` or `machinekit.Any()` to get the MK instance you want to
interact with and then use its `mdi(...)` member:
```
import machinekit
mk = machinekit.Any()
mk.mdi('G0X0Y0Z0')
```
MK's task mode is automatically switched to MDI if necessary.

## Error messages and notifications
Error messages are integrated into the FC log stream and show up like:
```
machinekit.ERROR: Can't issue MDI command when not homed
```

## Dependencies
* python3-pyftpdlib
* python3-protobuf
* python3-zeroconf
* python3-zmq
* machinekit-hal-posix

The only part used from `machinekit-hal-posix` are the Machinetalk python bindings. Unfortunately only
Python 2 bindings are installed. However, since it's all pure python we get away with a little manuall _installation_:

```
sudo cp -r /usr/lib/python2.7/dist-packages/machinetalk /usr/lib/python3/dist-packages
```

