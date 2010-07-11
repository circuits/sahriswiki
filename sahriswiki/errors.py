
from genshi import Markup

from circuits.web import Response
from circuits import handler, BaseComponent
from circuits.web.exceptions import HTTPException

class WikiError(HTTPException):
    """Base class for all error pages."""

class ForbiddenErr(WikiError):
    code = 403

class NotFoundErr(WikiError):
    code = 404

class UnsupportedMediaTypeErr(WikiError):
    code = 415

class NotImplementedErr(WikiError):
    code = 501

class ServiceUnavailableErr(WikiError):
    code = 503

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
