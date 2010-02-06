# Module:   plugins
# Author:   James Mills, prologic at shortcircuit dot net dot au
# Date:     6th February 2010

from . import BasePlugin

class HelloWorld(BasePlugin):

    def run(self, *args):
        pass

    def render(self):
        return "Hello World!"
