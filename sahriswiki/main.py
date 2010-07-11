#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""SahrisWiki - The logical wiki!

SahrisWiki is a new WikiWiki Engine designed for simplicity, flexibility
and ease of use.
"""

import os
import warnings
import optparse

from mercurial.hgweb import hgweb

from circuits.app import Daemon
from circuits import Manager, Debugger

from circuits.web import Logger, Server, Static
from circuits.web.wsgi import Application, Gateway

from root import Root
from config import Config
from env import Environment
from plugins import PluginManager
from tools import CacheControl, ErrorHandler, SignalHandler

def main():
    config = Config()
    config.parse_args()
    config.parse_files()

    manager = Manager()

    if config.get_bool("debug"):
        manager += Debugger(events=False)

    environ = Environment(config)

    manager += environ

    bind = environ.config.get("bind")
    if ":" in bind:
        address, port = bind.split(":")
        port = int(port)
    else:
        address, port = bind, environ.config.get_int("port")

    bind = (address, port)

    manager += (Server(bind) + Logger()
            + Root(environ)
            + CacheControl(environ)
            + ErrorHandler(environ)
            + SignalHandler(environ)
            + PluginManager(environ))

    if not environ.config.get_bool("disable-static"):
        manager += Static("/static", docroot=config.get("static"))

    if not environ.config.get_bool("disable-hgweb"):
        manager += Gateway(hgweb(environ.storage.repo_path), "/+hg")

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

    application = (Application()
            + environ
            + Root(environ)
            + CacheControl(environ)
            + ErrorHandler(environ)
            + PluginManager(environ))

    if not environ.config.get_bool("disable-static"):
        application += Static("/static", docroot=config.get("static"))

    if not environ.config.get_bool("disable-hgweb"):
        application += Gateway(hgweb(environ.storage.repo_path), "/+hg")
