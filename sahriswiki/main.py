#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""SahrisWiki - The logical wiki!

SahrisWiki is a new WikiWiki Engine designed for simplicity, flexibility
and ease of use.
"""

import os
import warnings
import optparse

try:
    import psyco
except ImportError:
    psyco = None

from mercurial.hgweb import hgweb

from circuits.app import Daemon
from circuits import Manager, Debugger
from circuits.net.pollers import Select, Poll

try:
    from circuits.net.pollers import EPoll
except ImportError:
    EPoll = None

from circuits.web import Logger, Server, Static
from circuits.web.wsgi import Application, Gateway

from root import Root
from tools import Tools
from env import Environment
from search import WikiSearch
from cache import CacheControl
from storage import WikiStorage
from plugins import PluginManager
from sahriswiki import __version__

USAGE = "%prog [options]"
VERSION = "%prog v" + __version__

def parse_options():
    """parse_options() -> opts, args

    Parse the command-line options given returning both
    the parsed options and arguments.
    """

    parser = optparse.OptionParser(usage=USAGE, version=VERSION)

    parser.add_option("-b", "--bind",
            action="store", type="string", default="0.0.0.0:8000",
            dest="bind",
            help="Bind to address:[port]")

    parser.add_option("-d", "--data-dir",
            action="store", type="string", default="wiki",
            dest="data",
            help="Location of data directory")

    parser.add_option("-c", "--cache-dir",
            action="store", type="string", default="cache",
            dest="cache",
            help="Location of cache directory")

    parser.add_option("", "--name",
            action="store", type="string", default="SahrisWiki",
            dest="name",
            help="Name")

    parser.add_option("", "--author",
            action="store", type="string", default="",
            dest="author",
            help="Author")

    parser.add_option("", "--keywords",
            action="store", type="string", default="",
            dest="keywords",
            help="Keywords")

    parser.add_option("", "--description",
            action="store", type="string", default=__doc__.split("\n")[0],
            dest="description",
            help="Description")

    parser.add_option("-f", "--front-page",
            action="store", type="string", default="FrontPage",
            dest="frontpage",
            help="Set main front page")

    parser.add_option("-e", "--encoding",
            action="store", type="string", default="utf-8",
            dest="encoding",
            help="Set encoding to read and write pages")

    parser.add_option("-l", "--language",
            action="store", type="string", default="en",
            dest="lang",
            help="Set language")

    parser.add_option("-r", "--read-only",
            action="store_true", default=False,
            dest="readonly",
            help="Set wiki in read-only mode")

    parser.add_option("-p", "--plugins",
            action="store", default="plugins",
            dest="plugins",
            help="Set directory where plugins are located")

    parser.add_option("", "--jit",
            action="store_true", default=False,
            dest="jit",
            help="Use python HIT (psyco)")

    parser.add_option("", "--multi-processing",
            action="store_true", default=False,
            dest="mp",
            help="Start in multiprocessing mode")

    parser.add_option("", "--poller",
            action="store", type="string", default="select",
            dest="poller",
            help="Specify type of poller to use")

    parser.add_option("", "--debug",
            action="store_true", default=False,
            dest="debug",
            help="Enable debug mode")

    parser.add_option("", "--pid-file",
            action="store", default=None,
            dest="pidfile",
            help="Write process id to pidfile")

    parser.add_option("", "--daemon",
            action="store_true", default=False,
            dest="daemon",
            help="Daemonize (fork into the background)")

    opts, args = parser.parse_args()

    return opts, args

def main():
    opts, args = parse_options()

    if opts.jit and psyco:
        psyco.full()

    if ":" in opts.bind:
        address, port = opts.bind.split(":")
        port = int(port)
    else:
        address, port = opts.bind, 8000

    bind = (address, port)

    manager = Manager()

    if opts.debug:
        manager += Debugger(events=False)

    poller = opts.poller.lower()
    if poller == "poll":
        Poller = Poll
    elif poller == "epoll":
        if EPoll is None:
            warnings.warn("No epoll support available.")
            Poller = Select
        else:
            Poller = EPoll
    else:
        Poller = Select

    storage = WikiStorage(opts.data, opts.encoding)
    search = WikiSearch(opts.cache, opts.lang, storage)

    environ = Environment(opts, storage, search)

    manager += environ

    htdocs = os.path.join(os.path.dirname(__file__), "htdocs")

    manager += (Poller() + Server(bind) + CacheControl(environ) + Logger()
            + Root(environ)
            + Tools(environ)
            + PluginManager(environ)
            + Static(docroot=htdocs)
            + Gateway(hgweb(storage.repo_path), "/+hg"))

    if opts.daemon:
        manager += Daemon(opts.pidfile)

    manager.run()

if __name__ in "__main__":
    main()
else:
    config = {"data": "wiki", "cache": "cache", "name": "SahrisWiki",
            "author": "", "keywords": "", "description": "",
            "frontpage": "FrontPage", "encoding": "utf-8", "lang": "en",
            "readonly": False, "plugins": "plugins"}

    class Options(object): pass
    opts = Options()
    opts.__dict__.update(config)

    storage = WikiStorage(opts.data, opts.encoding)
    search = WikiSearch(opts.cache, opts.lang, storage)

    environ = Environment(opts, storage, search)
    application = (Application()
            + environ
            + Root(environ)
            + CacheControl(environ)
            + PluginManager(environ)
            + Static(docroot="static")
            + Gateway(hgweb(storage.repo_path), "/+hg"))
