import os
import optparse
import ConfigParser

import sahriswiki

USAGE = "%prog [options]"
VERSION = "%prog v" + sahriswiki.__version__

class Config(object):

    default_filename = u"sahris.conf"

    def __init__(self, **kwargs):
        super(Config, self).__init__()

        self.config = dict(kwargs)
        self.parse_environ()

    def parse_environ(self):
        """Check the environment variables for options."""

        prefix = "SAHRIS_"
        for key, value in os.environ.iteritems():
            if key.startswith(prefix):
                name = key[len(prefix):].lower()
                self.config[name] = value

    def parse_args(self):
        self.options = []
        parser = optparse.OptionParser(usage=USAGE, version=VERSION)

        def add(*args, **kwargs):
            self.options.append(kwargs["dest"])
            parser.add_option(*args, **kwargs)

        add("-C", "--config", action="store", default=None,
                dest="config", metavar="FILE", type="string",
                help="Read configuration from FILE")

        add("-b", "--bind", action="store", default="0.0.0.0",
                dest="bind", metavar="INT", type="string",
                help="Listen on interface INT")

        add("-p", "--port", action="store", default=8000,
                dest="port", metavar="PORT", type="int", 
                help="Listen on port PORT")

        add("-d", "--data", action="store", default="wiki",
                dest="data", metavar="DIR", type="string",
                help="Store pages in DIR")

        add("-c", "--cache", action="store", default="cache",
                dest="cache", metavar="DIR", type="string",
                help="Store cache in DIR")

        add("-s", "--static", action="store",
                default=os.path.join(os.path.dirname(__file__), "static"),
                dest="static", metavar="DIR", type="string",
                help="Static files are located in DIR")

        add("-t", "--templates", action="store",
                default=os.path.join(os.path.dirname(__file__), "templates"),
                dest="templates", metavar="DIR", type="string",
                help="Templates are located in DIR")

        add("-i", "--index", action="store", default="FrontPage",
                dest="index", metavar="PAGE", type="string",
                help="Set index page to PAGE")

        add("-e", "--encoding", action="store", default="utf-8",
                dest="encoding", metavar="ENC", type="string",
                help="Use encoding ENC to read and write pages")

        add("-l", "--language", action="store", default="en",
                dest="language", metavar="LANG", type="string",
                help="Translate interface to LANG")

        add("", "--name", action="store", default=sahriswiki.__name__,
                dest="name", metavar="NAME", type="string",
                help="Set site name to NAME")

        add("", "--author", action="store", default=sahriswiki.__author__,
                dest="author", metavar="NAME", type="string",
                help="Set site author to NAME")

        add("", "--description", action="store",
                default=sahriswiki.__doc__.split("\n")[0],
                dest="description", metavar="DESC", type="string",
                help="Set site description to DESC")

        add("", "--keywords", action="store", default=sahriswiki.__keywords__,
                dest="keywords", metavar="KEYWORDS", type="string",
                help="Set site keywords to KEYWORDS")

        add("", "--readonly", action="store_true", default=False,
                dest="readonly", help="Set the wiki into readonly mode")

        add("", "--debug", action="store_true", default=False,
                dest="debug", help="Enable debugging mode")

        add("", "--daemon", action="store_true", default=False,
                dest="daemon", help="Run as a background process")

        add("", "--pid", action="store", default="sahris.pid",
                dest="pid", metavar="FILE", type="string",
                help="Write pid to FILE")

        add("", "--disable-hgweb", action="store_true", default=False,
                dest="disable-hgweb", help="Disable hgweb interface")

        add("", "--disable-static", action="store_true", default=False,
                dest="disable-static", help="Disable static file serving")

        options, args = parser.parse_args()

        for option, value in options.__dict__.iteritems():
            if option in self.options:
                if value is not None:
                    self.config[option] = value

    def parse_files(self, files=None):
        if files is None:
            files = [self.get("config", self.default_filename)]
        parser = ConfigParser.SafeConfigParser()
        parser.read(files)
        for section in parser.sections():
            for option, value in parser.items(section):
                self.config[option] = value

    def save_config(self, filename=None):
        """Saves configuration to a given file."""
        if filename is None:
            filename = self.default_filename

        parser = ConfigParser.RawConfigParser()
        section = self.config["name"]
        parser.add_section(section)
        for key, value in self.config.iteritems():
            parser.set(section, str(key), str(value))

        configfile = open(filename, "wb")
        try:
            parser.write(configfile)
        finally:
            configfile.close()

    def get(self, option, default=None):
        """
        Get the value of a config option or default if not set.

        >>> config = WikiConfig(option=4)
        >>> config.get("ziew", 3)
        3
        >>> config.get("ziew")
        >>> config.get("ziew", "ziew")
        "ziew"
        >>> config.get("option")
        4
        """

        return self.config.get(option, default)

    def get_bool(self, option, default=False):
        """
        Like get, only convert the value to True or False.
        """

        value = self.get(option, default)
        if value in (
            1, True,
            "True", "true", "TRUE",
            "1",
            "on", "On", "ON",
            "yes", "Yes", "YES",
            "enable", "Enable", "ENABLE",
            "enabled", "Enabled", "ENABLED",
        ):
            return True
        elif value in (
            None, 0, False,
            "False", "false", "FALSE",
            "0",
            "off", "Off", "OFF",
            "no", "No", "NO",
            "disable", "Disable", "DISABLE",
            "disabled", "Disabled", "DISABLED",
        ):
            return False
        else:
            raise ValueError("expected boolean value")

    def get_int(self, option, default=None):
        try:
            return int(self.config.get(option, default))
        except ValueError:
            return default

    def set(self, key, value):
        self.config[key] = value