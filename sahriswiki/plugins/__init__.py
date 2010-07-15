# Package:  plugins
# Author:   James Mills, prologic at shortcircuit dot net dot au
# Date:     6th February 2010

"""SahrisWiki Plugins

This package contains the  SahrisWiki Plugin Archiecture support providing
a common framework for all SahrisWiki Plugins.
"""

import os
import sys
from inspect import getmembers, isclass

from circuits import handler, BaseComponent
from circuits.web.controllers import expose, BaseController

class PluginManager(BaseComponent):

    """Manager for maintaining registered plugins

    The PluginManager manages a set of registered SahrisWiki plugins
    and loads a set of default plugins at startup.
    """

    def __init__(self, environ):
        super(PluginManager, self).__init__()

        self.environ = environ

    def loadPlugins(self, path):
        """Load all plugins on the path specified

        :param path: A path to the default set of plugins.
        :type path: str
        """

        if not path in sys.path:
            sys.path.append(path)

        __package__ = os.path.basename(path)

        p = lambda x: os.path.splitext(x)[1] == ".py"
        modules = [x for x in os.listdir(path)
                if p(x) and not x == "__init__.py"]

        for module in modules:
            name, _ = os.path.splitext(module)

            moduleName = "%s.%s" % (__package__, name)
            m = __import__(moduleName, globals(), locals(), __package__)

            p1 = lambda x: isclass(x) and issubclass(x, BasePlugin)
            p2 = lambda x: x is not BasePlugin
            predicate = lambda x: p1(x) and p2(x)
            plugins = getmembers(m, predicate)

            for name, Plugin in plugins:
                o = Plugin(self.environ)
                o.register(self)

    @handler("started", target="*")
    def _on_started(self, component, mode):
        """Started Event Handler

        When the system has started load the default set of plugins.

        :param component: The Component that caused the system startup
        :type component: instance of Manager
        
        :param mode: The startup mode ([T]hread, [P]rocess or None)
        :type mode: str or None
        """

        self.loadPlugins(os.path.abspath(self.environ.opts.plugins))

class BasePlugin(BaseController):

    """Base Component for all SahrisWiki plugins

    This is the Base Component for all SahrisWiki plugins and does nothing
    useful. Plugins should implement useful functionality by subclassing
    this Component and overriding defaults.
    """

    def __init__(self, environ):
        super(BasePlugin, self).__init__()

        self.environ = environ

    def render(self, template, **data):
        """Renger the given template with the supplied data

        :param template: The template to render
        :type template: str

        :param data: The dictionary of data to pass to the template context
        :type data: dict
        """

        return self.environ.render(template, **data)
