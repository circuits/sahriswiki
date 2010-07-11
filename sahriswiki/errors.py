
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
