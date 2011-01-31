# Module:   main
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Main

...
"""

import os
import sys

from mercurial.hgweb import hgweb

from circuits.app import Daemon
from circuits import Manager, Debugger

from circuits.web.wsgi import Application, Gateway
from circuits.web import Logger, Server, Sessions, Static

from root import Root
from config import Config
from env import Environment
from tools import CacheControl, Compression, ErrorHandler, SignalHandler

def main():
    config = Config()

    manager = Manager()

    if config.get("debug"):
        manager += Debugger(
            events=config.get("verbose"),
            file=config.get("errorlog"),
        )

    environ = Environment(config)

    manager += environ

    if config.get("sock") is not None:
        bind = config.get("sock")
    elif ":" in config.get("bind"):
        address, port = config.get("bind").split(":")
        bind = (address, int(port),)
    else:
        bind = (config.get("bind"), config.get("port"),)

    manager += (Server(bind)
            + Sessions()
            + Root(environ)
            + CacheControl(environ)
            + ErrorHandler(environ)
            + SignalHandler(environ))

    if not config.get("disable-logging"):
        manager += Logger(file=config.get("accesslog", sys.stdout))

    if not config.get("disable-static"):
        manager += Static(docroot=os.path.join(config.get("theme"), "htdocs"))

    if not config.get("disable-hgweb"):
        manager += Gateway(hgweb(environ.storage.repo_path), "/+hg")

    if not config.get("disable-compression"):
        manager += Compression(environ)

    if config.get("daemon"):
        manager += Daemon(config.get("pidfile"))

    manager.run()

if __name__ == "__main__":
    main()
