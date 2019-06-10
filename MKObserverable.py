

class MKObserverable(object):
    def __init__(self):
        self.observers = []

    def attach(self, observer):
        if not observer in self.observers:
            self.observers.append(observer)

    def detach(self, observer):
        self.observers = [o for o in self.observers if o != observer]

    def notifyObservers(self, arg):
        for observer in self.observers:
            observer.changed(self, arg)

