# Machinekit-Workbench
FreeCAD workbench for Machinekit integration in Python 3.

At least that's what it's supposed to be once it grows up - which might take a bit of time.

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

