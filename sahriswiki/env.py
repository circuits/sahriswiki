# Module:   env
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Environment Container

...
"""

import os
from hashlib import md5
from urllib import basejoin
from itertools import chain
from urlparse import urlparse

from circuits import handler, BaseComponent

from genshi import Markup
from genshi.template import TemplateLoader

from creoleparser import create_dialect, creole11_base, Parser

import macros
import sahriswiki
from utils import page_mime
from search import WikiSearch
from storage import WikiSubdirectoryIndexesStorage as DefaultStorage

from pagetypes import WikiPageText, WikiPageHTML, WikiPageImage
from pagetypes import WikiPageWiki, WikiPageFile, WikiPageLogout
from pagetypes import WikiPageColorText, WikiPageCSV, WikiPageRST
from pagetypes import WikiPageHello, WikiPageLogin, WikiPageAbout

class Environment(BaseComponent):

    filename_map = {
        "README":       (WikiPageText,  "text/plain"),
        "COPYING":      (WikiPageText,  "text/plain"),
        "CHANGES":      (WikiPageText,  "text/plain"),
        "MANIFEST":     (WikiPageText,  "text/plain"),
        "favicon.ico":  (WikiPageImage, "image/x-icon"),
    }

    mime_map = {
        "text":                     WikiPageText,
        "application/x-javascript": WikiPageColorText,
        "application/x-python":     WikiPageColorText,
        "text/csv":                 WikiPageCSV,
        "text/html":                WikiPageHTML,
        "text/x-rst":               WikiPageRST,
        "text/x-wiki":              WikiPageWiki,
        "image":                    WikiPageImage,
        "":                         WikiPageFile,
        "type/hello":               WikiPageHello,
        "type/login":               WikiPageLogin,
        "type/logout":              WikiPageLogout,
        "type/about":               WikiPageAbout,
    }

    def __init__(self, config):
        super(Environment, self).__init__()

        self.config = config

        self.storage = DefaultStorage(
            self.config.get("data"),
            self.config.get("encoding"),
            index=self.config.get("index"),
            indexes=self.config.get("indexes"),
        )

        self.search = WikiSearch(
            self.config.get("cache"),
            self.config.get("language"),
            self.storage,
        )

        self.parser = Parser(
            create_dialect(
                creole11_base,
                macro_func=macros.dispatcher,
                wiki_links_base_url="",
                wiki_links_class_func=self._wiki_links_class_func,
                wiki_links_path_func=self._wiki_links_path_func,
            ),
            method="xhtml"
        )

        template_config = {
            "allow_exec": False,
            "auto_reload": True,
            "default_encoding": self.config.get("encoding"),
            "search_path": [
                self.storage.path,
                os.path.join(self.config.get("theme"), "templates"),
            ],
            "variable_lookup": "lenient",
        }
            
        self.templates = TemplateLoader(**template_config)

        self.macros = macros.loadMacros()

        self.stylesheets = []
        self.version = sahriswiki.__version__

        self.site = {
            "name": self.config.get("name"),
            "author": self.config.get("author"),
            "keywords": self.config.get("keywords"),
            "description": self.config.get("description"),
        }

        self.users = self._create_users()

        self.request = None
        self.response = None

    def _config(self):
        """Return a safe config dict (with sensitive data removed)"""

        hidden = ("password",)

        config = self.config.copy()

        for key in hidden:
            if key in config:
                del config[key]

        return config

    def _login(self):
        return self.request.session.get("login", self.request.login)

    def _user(self):
        return self._login() or self.request.headers.get(
                "X-Forwarded-For", self.request.remote.ip)

    def _permissions(self):
        if self._login():
            yield "PAGE_EDIT"

    def _nav(self):
        yield

    def _metanav(self):
        if not self._login():
            yield ("Login", self.url("/+login"))
        else:
            yield ("Logout", self.url("/+logout"))

        yield ("Preferences", self.url("/+prefs"))
        yield ("Help/Guide",  self.url("/Help"))
        yield ("About",       self.url("/+about"))

    def _ctxnav(self, type="view", name=None):
        if name and type == "view":
            if self._login() or not self.config.get("readonly"):
                yield ("Edit", self.url("/+edit/%s" % name))
            yield ("Download", self.url("/+download/%s" % name))
            yield ("History",  self.url("/+history/%s" % name))
        elif type in ("index", "search"):
            yield ("Index",    self.url("/+search"))
            yield ("Orphaned", self.url("/+orphaned"))
            yield ("Wanted",   self.url("/+wanted"))
        elif type == "history":
            if name:
                yield ("RSS 1.0", self.url("/+feed/%s/?format=rss1") % name)
                yield ("RSS 2.0", self.url("/+feed/%s/?format=rss2") % name)
                yield ("Atom",    self.url("/+feed/%s/?format=atom") % name)
            else:
                yield ("RSS 1.0", self.url("/+feed/?format=rss1"))
                yield ("RSS 2.0", self.url("/+feed/?format=rss2"))
                yield ("Atom",    self.url("/+feed/?format=atom"))

    def _create_users(self):
        users = {"admin": md5(self.config.get("password")).hexdigest()}
        htpasswd = self.config.get("htpasswd", None)
        if htpasswd:
            f = open(htpasswd, "r")
            for line in f:
                line = line.strip()
                if line:
                    username, password = line.split(":")
                    users["username"] = password
            f.close()
        return users

    def _wiki_links_class_func(self, type, url, body, name):
        if type == "wiki" and name:
            if name in self.storage:
                return "wiki"
            else:
                return "wiki new"
        elif type == "url":
            base = urlparse(self.url("/"))
            link = urlparse(url)
            if not all([base[i] == link[i] for i in range(2)]):
                return "external"

    def _wiki_links_path_func(self, tag, path):
        if tag == "img":
            return self.url("/+download", path)
        elif type == "wiki":
            if hasattr(self.storage, "is_index"):
                if self.storage.is_index(path):
                    return os.path.join(path, "/")
            return path
        else:
            return path

    def url(self, *args):
        return self.request.url("/".join(args))

    def staticurl(self, url):
        base = self.config.get("static-baseurl", None)
        if base:
            return basejoin(base, url)
        else:
            return self.request.url("/%s" % url)

    def get_page(self, name):
        """Creates a page object based on page"s mime type"""

        try:
            page_class, mime = self.filename_map[name]
        except KeyError:
            mime = page_mime(name)
            major, minor = mime.split("/", 1)
            try:
                page_class = self.mime_map[mime]
            except KeyError:
                try:
                    page_class = self.mime_map[major]
                except KeyError:
                    page_class = self.mime_map[""]

        return page_class(self, name, mime)

    def include(self, name, context=None):
        if name in self.storage:
            return self.parser.generate(self.storage.page_text(name),
                environ=(self, context))
        else:
            return Markup("<!-- SiteMenu Not Found -->")

    def render(self, template, **data):
        data.update({
            "sahriswiki": {
                "version": sahriswiki.__version__
            },
            "url":         self.url,
            "site":        self.site,
            "include":     self.include,
            "config":      self._config(),
            "staticurl":   self.staticurl,
            "permissions": self._permissions(),
            "nav":         chain(self._nav(), data.get("nav", [])),
            "ctxnav":      chain(self._ctxnav(), data.get("ctxnav", [])),
            "metanav":     chain(self._metanav(), data.get("metanav", [])),
        })
        t = self.templates.load(template)
        return t.generate(**data).render("xhtml", doctype="html")

    @handler("request", priority=1.0, target="web")
    def _on_request(self, request, response):
        self.request = request
        self.response = response
