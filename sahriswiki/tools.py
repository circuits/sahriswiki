import os
import signal

from genshi import Markup

from mercurial.node import short

from circuits.web import Response
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
        data["description"] = Markup(data["description"])
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
