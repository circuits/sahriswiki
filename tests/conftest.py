# Module:   conftest
# Date:     6th December 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""py.test config"""

import pytest

import sys
import threading
from time import sleep
from collections import deque

from circuits.core.manager import TIMEOUT
from circuits import handler, BaseComponent, Debugger, Manager


class Watcher(BaseComponent):

    def init(self):
        self._lock = threading.Lock()
        self.events = deque()

    @handler(channel="*", priority=999.9)
    def _on_event(self, event, *args, **kwargs):
        with self._lock:
            self.events.append(event)

    def wait(self, name, channel=None, timeout=3.0):
        for i in range(int(timeout / TIMEOUT)):
            if channel is None:
                with self._lock:
                    for event in self.events:
                        if event.name == name:
                            return True
            else:
                with self._lock:
                    for event in self.events:
                        if event.name == name and channel in event.channels:
                            return True
            sleep(TIMEOUT)


class Flag(object):
    status = False


@pytest.fixture(scope="session")
def manager(request):
    manager = Manager()
    watcher = Watcher().register(manager)

    def finalizer():
        manager.stop()

    request.addfinalizer(finalizer)

    watcher.wait("started")
    watcher.unregister()

    if request.config.option.verbose:
        Debugger().register(manager)

    return manager


@pytest.fixture
def watcher(request, manager):
    watcher = Watcher().register(manager)

    def finalizer():
        watcher.unregister()

    return watcher


def pytest_namespace():
    return dict((
        ("PYVER", sys.version_info[:3]),
    ))
