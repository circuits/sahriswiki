import os
import signal

from genshi import Markup

from mercurial.node import short

from circuits.web import Response
from circuits.web.tools import gzip
from circuits import handler, BaseComponent
from circuits.web.tools import validate_etags

class CacheControl(BaseComponent):

    channel = "web"

    def __init__(self, environ):
        super(CacheControl, self).__init__()

        self.environ = environ

    @handler("request", filter=True, priority=100.0)
    def _on_request(self, request, response):
        node = short(self.environ.storage.repo_node())
        response.headers.add_header("ETag", node)
        response = validate_etags(request, response)
        if response:
            return response

class Compression(BaseComponent):

    channel = "web"

    mime_types = ["text/plain", "text/html", "text/css"]

    @handler("response_started")
    def _on_response_started(self, event, response_event):
        response = response_event[0]
        ct = response.headers.get("Content-Type", "text/html").split(";")[0]
        print ct
        import pdb
        pdb.set_trace()
        gzip(response, mime_types=self.mime_types)

class ErrorHandler(BaseComponent):

    channel = "web"

    def __init__(self, environ):
        super(ErrorHandler, self).__init__()

        self.environ = environ
        self.render = self.environ.render

    @handler("httperror", filter=True)
    def _on_httperror(self, event, request, response, code, **kwargs):
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

    @handler("stopped", target="*")
    def _on_stopped(self, component):
        if self.environ.config.get("config"):
            self.environ.config.save_config()
