# Implementation of an intrusive observer pattern

class MKObserverable(object):
    '''Internal base class for propagating changes to an arbitrary list of observers.'''
    def __init__(self):
        self.observers = []

    def attach(self, observer):
        '''attach(observer) ... registers the given observer to be notified by changes
        of the receiver. The observer is expected to implement the changed(arg) member
        which will be invoked by the receiver on changes.'''
        if not observer in self.observers:
            self.observers.append(observer)

    def detach(self, observer):
        '''detach(observer) ... remove observer from the list of observers and it will
        no longer be notified.'''
        self.observers = [o for o in self.observers if o != observer]

    def notifyObservers(self, arg):
        '''Internal member to trigger the notification of the receiver's observers.'''
        for observer in self.observers:
            observer.changed(self, arg)

