# Module:   config
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Configuration Handling

...
"""

import os
import ConfigParser
from warnings import warn

from argparse import ArgumentParser

import reprconf
import sahriswiki

class Config(reprconf.Config):

    prefix = "SAHRIS_"

    def __init__(self, file=None, **kwargs):
        super(Config, self).__init__(file, **kwargs)

        self.parse_environ()
        self.parse_options()
        self.check_options()

    def check_options(self):
        paths = ("accesslog", "config", "repo", "errorlog",
                "pidfile", "sock", "theme",)

        for path in paths:
            value = self.get(path, None)
            if value and not os.path.isabs(value):
                self[path] = os.path.abspath(os.path.expanduser(value))

    def parse_environ(self):
        """Check the environment variables for options."""

        config = {}

        for key, value in os.environ.iteritems():
            if key.startswith(self.prefix):
                name = key[len(self.prefix):].lower()
                config[name] = value

        self.update(config)

    def parse_options(self):
        parser = ArgumentParser(sahriswiki.__name__)

        add = parser.add_argument

        add("--config", action="store", default=None,
                dest="config", metavar="FILE", type=str,
                help="Read configuration from FILE")

        add("-b", "--bind", action="store", default="0.0.0.0",
                dest="bind", metavar="INT", type=str,
                help="Listen on interface INT")

        add("-p", "--port", action="store", default=8000,
                dest="port", metavar="PORT", type=int,
                help="Listen on port PORT")

        add("-s", "--sock", action="store", default=None,
                dest="sock", metavar="FILE", type=str,
                help="Listen on socket FILE")

        add("-r", "--repo", action="store", default="wiki",
                dest="repo", metavar="REPO", type=str,
                help="Store pages in mercurial repository REPO")

        add("-d", "--database", action="store",
                default="sqlite:///sahriswiki.db",
                dest="db", metavar="DB", type=str,
                help="Store meta data in database DB")

        add("-t", "--theme", action="store",
                default=os.path.join(os.path.dirname(__file__)),
                dest="theme", metavar="DIR", type=str,
                help="Set theme (static and templates) path to DIR")

        add("--frontpage", action="store", default="FrontPage",
                dest="frontpage", metavar="PAGE", type=str,
                help="Set default front page to PAGE")

        add("--index", action="store", default="Index",
                dest="index", metavar="PAGE", type=str,
                help="Set default index page to PAGE")

        add("--indexes", action="store", nargs="+",
            default=["Index", "index.html", "index.rst"],
            dest="indexes", metavar="LIST", type=list,
            help="Set index search list to LIST")

        add("--menu", action="store", default="SiteMenu",
                dest="menu", metavar="PAGE", type=str,
                help="Set default site menu page to PAGE")

        add("--encoding", action="store", default="utf-8",
                dest="encoding", metavar="ENC", type=str,
                help="Use encoding ENC to read and write pages")

        add("--language", action="store", default="en",
                dest="language", metavar="LANG", type=str,
                help="Translate interface to LANG")

        add("--name", action="store", default=sahriswiki.__name__,
                dest="name", metavar="NAME", type=str,
                help="Set site name to NAME")

        add("--author", action="store", default=sahriswiki.__author__,
                dest="author", metavar="NAME", type=str,
                help="Set site author to NAME")

        add("--description", action="store",
                default=sahriswiki.__doc__.split("\n")[0],
                dest="description", metavar="DESC", type=str,
                help="Set site description to DESC")

        add("--keywords", action="store", default="sahriswiki",
                dest="keywords", metavar="KEYWORDS", type=str,
                help="Set site keywords to KEYWORDS")

        add("--readonly", action="store_true", default=False,
                dest="readonly",
                help="Set the wiki into readonly mode")

        add("--debug", action="store_true", default=False,
                dest="debug",
                help="Enable debugging mode")

        add("--daemon", action="store_true", default=False,
                dest="daemon",
                help="Run as a background process")

        add("--verbose", action="store_true", default=False,
                dest="verbose",
                help="Enable verbose debugging")

        add("--errorlog", action="store", default=None,
                dest="errorlog", metavar="FILE", type=str,
                help="Store debug and error information in FILE")

        add("--accesslog", action="store", default=None,
                dest="accesslog", metavar="FILE", type=str,
                help="Store web server access logs in FILE")

        add("--pidfile", action="store", default="sahris.pid",
                dest="pidfile", metavar="FILE", type=str,
                help="Write process id to FILE")

        add("--disable-hgweb", action="store_true", default=False,
                dest="disable-hgweb",
                help="Disable hgweb interface")

        add("--disable-logging", action="store_true", default=False,
                dest="disable-logging",
                help="Disable access logging")

        add("--disable-static", action="store_true", default=False,
                dest="disable-static",
                help="Disable static file serving")

        add("--disable-compression", action="store_true", default=False,
                dest="disable-compression",
                help="Disable compression")

        add("--static-baseurl", action="store", default=None,
                dest="static-baseurl", metavar="URL", type=str,
                help="Set static baseurl to URL")

        namespace = parser.parse_args()

        if namespace.config is not None:
            filename = os.path.abspath(os.path.expanduser(namespace.config))
            if os.path.exists(filename) and os.path.isfile(filename):
                config = reprconf.as_dict(filename)
                if config.keys():
                    config = config[config.keys()[0]]
                    for option, value in config.iteritems():
                        if option in namespace:
                            self[option] = value
                        else:
                            warn("Ignoring unknown option %r" % option)

        for option, value in namespace.__dict__.iteritems():
            if option not in self and value is not None:
                self[option] = value

    def reload_config(self):
        filename = self.get("config")
        if filename is not None:
            config = reprconf.as_dict(filename)
            self.update(config.get(config.keys()[0], {}))

    def save_config(self, filename=None):
        if filename is None:
            filename = self.get("config", "sahris.conf")

        parser = ConfigParser.RawConfigParser()
        section = self.get("name", "sahris")
        parser.add_section(section)
        for key, value in self.iteritems():
            parser.set(section, str(key), repr(value))

        configfile = open(filename, "wb")
        try:
            parser.write(configfile)
        finally:
            configfile.close()
