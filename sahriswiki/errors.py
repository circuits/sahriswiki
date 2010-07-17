# Module:   errors
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Error Definitions

...
"""

from circuits.web.exceptions import HTTPException

class WikiError(HTTPException):
    """Base class for all error pages."""

    traceback = False

class ForbiddenErr(WikiError):

    code = 403

class NotFoundErr(WikiError):

    code = 404

class UnsupportedMediaTypeErr(WikiError):

    code = 415

class NotImplementedErr(WikiError):

    code = 501

    description = (
        "<p>This feature has not yet been implemented."
        "Please come back and try again later.</p>"
    )

class ServiceUnavailableErr(WikiError):

    code = 503
