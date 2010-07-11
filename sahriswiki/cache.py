from mercurial.node import short

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
