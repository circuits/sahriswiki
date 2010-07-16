# Module:   tools
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Tools and Filters

...
"""

import os
import signal
from hashlib import md5
from marshal import dumps

from genshi import Markup

from mercurial.node import short

from circuits.web import Response
from circuits.web.tools import gzip
from circuits import handler, BaseComponent
from circuits.web.tools import validate_etags

import sahriswiki

class CacheControl(BaseComponent):

    channel = "web"

    def __init__(self, environ):
        super(CacheControl, self).__init__()

        self.environ = environ

    @handler("request", filter=True, priority=1.0)
    def _on_request(self, request, response):
        if request.path in ("/+login", "/+logout"):
            return

        repo = short(self.environ.storage.repo_node())
        sess = md5(dumps(request.session)).hexdigest()
        config = md5(dumps(self.environ.config.copy())).hexdigest()
        version = sahriswiki.__version__

        etag = "%s/%s/%s/%s" % (repo, sess, config, version)

        response.headers.add_header("ETag", etag)
        response = validate_etags(request, response)
        if response:
            return response

class Compression(BaseComponent):

    channel = "web"

    mime_types = ["text/plain", "text/html", "text/css"]

    @handler("response_started")
    def _on_response_started(self, event, response_event):
        response = response_event[0]
        gzip(response, mime_types=self.mime_types)

class ErrorHandler(BaseComponent):

    channel = "web"

    def __init__(self, environ):
        super(ErrorHandler, self).__init__()

        self.environ = environ
        self.render = self.environ.render

    @handler("httperror", filter=True)
    def _on_httperror(self, event, request, response, code, **kwargs):
        self.environ.request = request
        self.environ.response = response
        data = event.data.copy()
        data["title"] = "Error"
        data["traceback"] = Markup(data["traceback"])
        data["description"] = Markup(data["description"] or u"")
        response.body = self.render("error.html", **data)
        return self.push(Response(response))

class SignalHandler(BaseComponent):

    def __init__(self, environ):
        super(SignalHandler, self).__init__()

        self.environ = environ

    @handler("signal", target="*")
    def _on_signal(self, sig, stack):
        if os.name == "posix" and sig == signal.SIGHUP:
            self.storage.reopen()
            self.environ.config.reload_config()
