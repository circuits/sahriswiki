# Module:   plugins
# Author:   James Mills, prologic at shortcircuit dot net dot au
# Date:     6th February 2010

"""HelloWorld Plugin

...
"""

from circuits.web import expose

from . import BasePlugin

class HelloWorld(BasePlugin):

    @expose("+hello")
    def hello(self, *args, **kwargs):
        page = {"name": "HelloWorld",
                "text": "Hello World!"}

        data = {"page": page}

        return self.render("view.html", **data)
