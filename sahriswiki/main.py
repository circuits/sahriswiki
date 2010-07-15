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
from plugins import PluginManager
from tools import CacheControl, Compression, ErrorHandler, SignalHandler

def main():
    config = Config()
    config.parse_args()
    config.parse_files()

    manager = Manager()

    if config.get_bool("debug"):
        manager += Debugger(events=config.get("verbose"))

    environ = Environment(config)

    manager += environ

    bind = config.get("bind")
    if ":" in bind:
        address, port = bind.split(":")
        port = int(port)
    else:
        address, port = bind, config.get_int("port")

    bind = (address, port)

    manager += (Server(bind)
            + Sessions()
            + Root(environ)
            + CacheControl(environ)
            + ErrorHandler(environ)
            + SignalHandler(environ)
            + PluginManager(environ))

    if not config.get_bool("disable-logging"):
        manager += Logger(file=config.get("logfile", sys.stderr))

    if not config.get_bool("disable-static"):
        manager += Static(docroot=os.path.join(config.get("theme"), "htdocs"))

    if not config.get_bool("disable-hgweb"):
        manager += Gateway(hgweb(environ.storage.repo_path), "/+hg")

    if not config.get_bool("disable-compression"):
        manager += Compression(environ)

    if config.get_bool("daemon"):
        manager += Daemon(config.get("pid"))

    manager.run()

if __name__ in "__main__":
    main()
else:
    config = Config()
    config.parse_args()
    config.parse_files()

    environ = Environment(config)

    application = (Application() + Sessions()
            + environ
            + Root(environ)
            + CacheControl(environ)
            + ErrorHandler(environ)
            + PluginManager(environ))

    if not config.get_bool("disable-static"):
        application += Static(
            docroot=os.path.join(config.get("theme"), "htdocs")
        )

    if not config.get_bool("disable-hgweb"):
        application += Gateway(hgweb(environ.storage.repo_path), "/+hg")
