# MachinekitInstance
#
# The classes in this file deal with service discovery and keep track of all discovered Machinekit
# instances and their associated endpoints.

import MachinekitPreferences
import copy
import itertools
import json
import threading
import time
import urllib.request
import zeroconf

class ServiceEndpoint(object):
    '''POD for describing a service end point.'''

    def __init__(self, service, name, addr, prt, properties):
        self.service = service
        self.name = name
        self.addr = addr
        self.prt = prt
        self.properties = properties
        self.dsn = properties[b'dsn']
        self.uuid = properties[b'instance']

    def __str__(self):
        return "%s@%s:%d" % (self.service, self.address(), self.port())

    def addressRaw(self):
        '''Return the endoint address in its raw format.'''
        return self.addr

    def address(self):
        '''Return the endpoint address as an IPv4 string.'''
        if str == type(self.addr):
            return self.addr
        return "%d.%d.%d.%d" % (self.addr[0], self.addr[1], self.addr[2], self.addr[3])

    def port(self):
        '''Return the endpoint port number.'''
        return self.prt

class MachinekitInstance(object):
    '''Representation of a discovered MK instance, tying all associated services together.'''

    def __init__(self, uuid, properties):
        self.uuid = uuid
        self.properties = properties
        self.endpoint = {}
        self.lock = threading.Lock()

    def __str__(self):
        with self.lock:
            return "MK(%s): %s" % (self.uuid.decode(), sorted([ep.service for epn, ep in self.endpoint.items()]))

    def _addService(self, properties, name, address, port):
        s = properties[b'service'].decode()
        with self.lock:
            endpoint = ServiceEndpoint(s, name, address, port, properties)
            self.endpoint[s] = endpoint

    def _removeService(self, name):
        with self.lock:
            for epn, ep in self.endpoint.items():
                if ep.name == name:
                    del self.endpoint[epn]
                    break

    def endpointFor(self, service):
        '''endpointFor(service) ... return the MK endpoint for the given service.'''
        with self.lock:
            return self.endpoint.get(service)

    def services(self):
        '''services() ... returns the list of service names discovered for this MK instance.'''
        with self.lock:
            return [service for service in self.endpoint]

def serviceThread(monitor):
    issue = {}
    while True:
        with monitor.lock:
            explicit = copy.copy(monitor.explicit)
        for host in explicit:
            if not ':' in host:
                host += ':8088'
            try:
                s = urllib.request.urlopen("http://%s/machinekit" % host).read()
                j = json.loads(s)
                #print('serivces:', [j[k] for k in j])
                with monitor.lock:
                    mk = None
                    for name in j:
                        props = j[name]
                        properties = {}
                        for l in props:
                            properties[l.encode()] = props[l].encode()
                        uuid = properties[b'uuid']
                        mk = monitor.instance.get(uuid)
                        if mk is None:
                            mk = MachinekitInstance(uuid, properties)
                            monitor.instance[uuid] = mk
                        if mk.endpointFor(name) is None:
                            dsn = props['dsn'].split(':')
                            mk._addService(properties, name, dsn[1].strip('/'), int(dsn[2]))
                    if not mk is None:
                        for service in mk.services():
                            if j.get(service) is None:
                                mk._removeService(service)
                issue[host] = None
            except Exception as e:
                # this happens when MK isn't running or the host isn't even routable
                err = str(e)
                if issue.get(host) != err:
                    print("%s - %s" % (host, err))
                    issue[host] = err

        time.sleep(1)



class ServiceMonitor(object):
    '''Singleton for the zeroconf service discovery. DO NOT USE.'''
    _Instance = None

    def __init__(self, explicit=None):
        self.zc = zeroconf.Zeroconf()
        self.browser = zeroconf.ServiceBrowser(self.zc, "_machinekit._tcp.local.", self)
        self.instance = {}
        self.explicit = explicit if explicit else MachinekitPreferences.restServers()
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=serviceThread, args=(self,), daemon=True)
        self.thread.start()

    # zeroconf.ServiceBrowser interface
    def remove_service(self, zc, typ, name):
        with self.lock:
            for mkn, mk in self.instance.items():
                mk._removeService(name)

    def add_service(self, zc, typ, name):
        info = zc.get_service_info(typ, name)
        if info and info.properties.get(b'service'):
            with self.lock:
                uuid = info.properties[b'uuid']
                mk = self.instance.get(uuid)
                if not mk:
                    mk = MachinekitInstance(uuid, info.properties)
                    self.instance[uuid] = mk
                mk._addService(info.properties, info.name, info.address, info.port)
        else:
            name = ' '.join(itertools.takewhile(lambda s: s != 'service', info.name.split()))
            PathLog.info("machinetalk.%-13s - no info" % (name))

    def instances(self, services):
        with self.lock:
            return [mk for mkn, mk in self.instance.items() if services is None or mk.providesServices(services)]

