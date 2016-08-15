"""WSGI Compatibility

This module implements a WSGI Application that can be loded by mod_wsgi
or uwsgi.
"""

import os

from mercurial.ui import ui
from mercurial.hgweb import hgweb

from circuits import Debugger
from circuits.web import Sessions, Static
from circuits.web.wsgi import Application, Gateway

from .root import Root
from .config import Config
from .env import Environment
from .tools import ErrorHandler, CacheControl, Compression


config = Config()

environ = Environment(config)

application = Application()

application += Debugger()
application += Sessions()
application += Root(environ)
application += CacheControl(environ)
application += ErrorHandler(environ)

application += environ

if not config.get("disable-static"):
    application += Static(docroot=os.path.join(config.get("theme"), "htdocs"))

if not config.get("disable-hgweb"):
    baseui = ui()
    baseui.setconfig("web", "prefix", "/+hg")
    baseui.setconfig("web", "style", "gitweb")
    baseui.setconfig("web", "allow_push", "*")
    baseui.setconfig("web", "push_ssl", False)
    baseui.setconfig("web", "allow_archive", ["bz2", "gz", "zip"])
    baseui.setconfig("web", "description", config.get("description"))

    application += Gateway({
        "/+hg": hgweb(
            environ.storage.repo_path,
            config.get("name"),
            baseui
        )
    })

if not config.get("disable-compression"):
    application += Compression(environ)
