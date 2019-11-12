# Currently not used - the 'file' service seems a bit elusive to generalise.
# Its functionality is currently split in 'machinekit.py' and 'MachinekitExecute.py'

from MKService import *
from ftplib import FTP
from urlparse import urlparse


class MKServiceFile(MKService):

    def __init__(self, context, name, properties):
        MKService.__init__(self, name, properties)
        self.up = urlparse(self.dsn)

    def process(self, container):
        raise Exception("got: %s" % str(container))

    def uploadFile(self, fname):
        pass
