# Machinekit-Workbench
FreeCAD workbench for Machinekit integration in Python 3 of an XYZ cnc.

At least that's what it's supposed to be once it grows up - which might take a bit of time.

There are currently 4 interfaces available:
* Hud     ... Head Up Display of coordinates and tool in the 3d view
* Setup   ... jogging and setting the coordinate offset
* Execute ... load, run/pause/stop Path Jobs in MK
* MDI     ... console interface to issue MDI commands

## Hud
The Hud is pretty straight forward and currently non-configurable. The tool is blue-ish when the spindle
is not turned on or the spindle speed is `0`. If the spindle is enabled and it's speed is not `0` it turns
red-ish.

## Setup
The Setup dock widget provides an interface to jog the tool around and to set the offset of the coordinate system.
It's title inidcates the name of the MK instance it is connected to.

### DRO
The DRO displays the actual position of each axis. The current position can be set by changing the value in the
spinbox and activating it by pressing the corresponding axis button.

Shortcut buttons are available to set the coordinate(s) to `0`

### Jog
The `Z` and `XY` buttons jog the tool to the `0` position of the respective axes. If `Continuous` is pressed
jogging continues for as long as a button is pressed, otherwise the fixed distance of the combo box is jogged
in the button's direction.

While `Move Gantry` is pressed the user can click a point in the 3d view and MK will jog the tool to that location.
Initially only the `XY` axes are modified - however a second click on the same location also jogs the `Z` axis.

## Execute
In order to load a Job into MK one selects the Job in the Tree and then presses `Load`. Once a job is loaded
the title of the dock widget is changed to the label of the Job and the `Run` and `Step` buttons are enabled.

The bottom slider and spinbox represent the feed override value. The feed rate is changed once the slider is
released or, if the value is entered directly into the spinbox, editing is finished. Note that only the feed
rate is scaled and not the rapid rate. It is assumed that rapid moves are always performed at the max speed.

At the very bottom is a status bar which is currently used for debugging - the most useful info is displayed
at the end where the current line number and total number of lines are displayed.

## MDI
In order to use the MDI interface one must import the `machinekit` module and then call `MDI(..)`
```
import machinekit
machinekit.MDI('G0X0Y0')
```

## Error messages and notifications
Error messages are integrated into the FC log stream and show up like:
```
machinekit.ERROR: Can't issue MDI command when not homed
```

## Dependencies
* python3-pyftplib
* python3-protobuf
* python3-zeroconf
* python3-zmq
* machinekit-hal-posix

The only part used from `machinekit-hal-posix` are the Machinetalk python bindings. Unfortunately only
Python 2 bindings are installed but since it's all pure python we get away with a little manuall _installation_:

```
sudo cp -r /usr/lib/python2.7/dist-packages/machinetalk /usr/lib/python3/dist-packages
```

