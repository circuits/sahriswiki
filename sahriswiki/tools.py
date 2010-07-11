import os
import signal

from circuits import handler, BaseComponent

class Tools(BaseComponent):

    def __init__(self, environ):
        super(Tools, self).__init__()

        self.environ = environ

    @handler("signal", target="*")
    def _on_signal(self, sig, stack):
        if os.name == "posix" and sig == signal.SIGHUP:
            self.storage.reopen()
