# Package:  plugins
# Author:   James Mills, prologic at shortcircuit dot net dot au
# Date:     6th February 2010

"""SahrisWiki Plugins

This package contains default SahrisWiki Plugins
"""

from circuits.web import Controller

class BasePlugin(Controller):

    def __init__(self, pluginmanager, opts, storage, search):
        super(BasePlugin, self).__init__()

        self.pluginmanager = pluginmanager
        self.opts = opts
        self.storage = storage
        self.search = search
