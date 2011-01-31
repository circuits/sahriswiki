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

from genshi.builder import tag
from genshi.template import TemplateLoader

from creoleparser import create_dialect, creole11_base, Parser

import macros
import schema
import sahriswiki
from utils import page_mime
from auth import Permissions
from search import WikiSearch
from dbm import DatabaseManager
from storage import WikiSubdirectoryIndexesStorage as DefaultStorage

from pagetypes import WikiPageText, WikiPageHTML
from pagetypes import WikiPageWiki, WikiPageFile, WikiPageImage
from pagetypes import WikiPageColorText, WikiPageCSV, WikiPageRST

class Environment(BaseComponent):

    filename_map = {
        "README":       (WikiPageText,  "text/plain"),
        "COPYING":      (WikiPageText,  "text/plain"),
        "CHANGES":      (WikiPageText,  "text/plain"),
        "MANIFEST":     (WikiPageText,  "text/plain"),
        "LICENSE":      (WikiPageText,  "text/plain"),
        "ChangeLog":    (WikiPageText,  "text/plain"),
        "favicon.ico":  (WikiPageImage, "image/x-icon"),
    }

    mime_map = {
        "text":                     WikiPageText,
        "application/javascript":   WikiPageColorText,
        "text/x-python":            WikiPageColorText,
        "text/css":                 WikiPageColorText,
        "text/csv":                 WikiPageCSV,
        "text/html":                WikiPageHTML,
        "text/x-rst":               WikiPageRST,
        "text/x-wiki":              WikiPageWiki,
        "image":                    WikiPageImage,
        "":                         WikiPageFile,
    }

    def __init__(self, config):
        super(Environment, self).__init__()

        self.config = config

        self.dbm = DatabaseManager(self.config.get("db"),
            echo=(self.config.get("debug") and self.config.get("verbose")),
        ).register(self)

        self.storage = DefaultStorage(
            self.config.get("repo"),
            self.config.get("encoding"),
            index=self.config.get("index"),
            indexes=self.config.get("indexes"),
        )

        self.search = WikiSearch(
            self.dbm.session,
            self.config.get("language"),
            self.storage,
        )

        self.parser = Parser(
            create_dialect(
                creole11_base,
                macro_func=macros.dispatcher,
                wiki_links_base_url="/",
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

        self.request = None
        self.response = None

    def _login(self):
        return self.request.session.get("login", self.request.login)

    def _user(self):
        return self._login() or self.request.headers.get(
                "X-Forwarded-For", self.request.remote.ip)

    def _permissions(self):
        return Permissions(self, self._login())

    def _metanav(self):
        yield ("About",       self.url("/+about"),    )
        yield ("Help",        self.url("/Help"),      )
        yield ("History",     self.url("/+history"),  )

        if not self._login():
            yield ("Login",   self.url("/+login"),    )
        else:
            yield ("Logout",  self.url("/+logout"),   )
            yield ("Profile", self.url("/+profile"),  )

        yield ("Register",    self.url("/+register"), )

    def _ctxnav(self, type="view", name=None):
        permissions = self._permissions()
        if name and type == "view":
            yield ("Functions",     self._ctxnav("func", name),)
            yield ("Information",   self._ctxnav("info", name),)
            yield ("Miscellaneous", self._ctxnav("misc", name),)
        elif type in ("index", "search"):
            yield ("Index",         self.url("/+search"))
            yield ("Orphaned",      self.url("/+orphaned"))
            yield ("Wanted",        self.url("/+wanted"))
        elif type == "history":
            if name:
                yield ("RSS 1.0",   self.url("/+feed/%s/?format=rss1") % name)
                yield ("RSS 2.0",   self.url("/+feed/%s/?format=rss2") % name)
                yield ("Atom",      self.url("/+feed/%s/?format=atom") % name)
            else:
                yield ("RSS 1.0",   self.url("/+feed/?format=rss1"))
                yield ("RSS 2.0",   self.url("/+feed/?format=rss2"))
                yield ("Atom",      self.url("/+feed/?format=atom"))
        elif name and type == "func":
            if "PAGE_EDIT" in permissions:
                yield ("Edit",      self.url("/+edit/%s" % name))
            if "PAGE_DELETE" in permissions:
                yield ("Delete",    self.url("/+delete/%s" % name))
            if "PAGE_RENAME" in permissions:
                yield ("Rename",    self.url("/+rename/%s" % name))
        elif name and type == "info":
            yield ("History",       self.url("/+history/%s" % name))
            yield ("Feeds",          self._ctxnav("history", name))
        elif name and type == "misc":
            yield ("Download",      self.url("/+download/%s" % name))
            if "PAGE_UPLOAD" in permissions:
                yield ("Upload",    self.url("/+upload/%s" % name))

    def _breadcrumbs(self, page=None):
        yield ("", "Home", "Home",)
        if page and "name" in page:
            xs = []
            name = page["name"]
            if not name == self.config.get("frontpage"):
                parts = name.split("/")
                for x in parts[:-1]:
                    xs.append(x)
                    yield ("/".join(xs), x, x,)
                base = os.path.basename(name)
                yield ("+backlinks/%s" % name, base, "View BackLinks",)

    def _wiki_links_class_func(self, type, url, body, name):
        if type == "wiki":
            if url and url[0] == ".":
                url = url[1:]
            if url and url[0] in "./":
                url = url[1:]
            if url and url[0] == "/":
                url = url[1:]
            if url in self.storage:
                return "wiki"
            else:
                return "wiki new"
        elif type == "url":
            base = urlparse(self.url("/"))
            link = urlparse(url)
            if not all([base[i] == link[i] for i in range(2)]):
                return "external"

    def _wiki_links_path_func(self, tag, path, (environ, context)):
        if tag == "img":
            return self.url("/+download", path)
        elif tag == "a":
            if path.startswith(".."):
                path = path[2:]
                if path and path[0] == "/":
                    path = path[1:]
                dirname = os.path.dirname(context["page"]["name"])
                return os.path.join(dirname, path)
            elif path.startswith("."):
                path = path[1:]
                if path and path[0] == "/":
                    path = path[1:]
                return os.path.join(context["page"]["name"], path)
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

    def include(self, name, parse=True, context="block", data=None):
        if name in self.storage:
            text = self.storage.page_text(name)
            if parse:
                return self.parser.generate(text, context=context,
                        environ=(self, data))
            else:
                return tag.pre(text)
        else:
            return tag.div(tag.p(u"Page %s Not Found" % name), class_="error")

    def render(self, template, **data):
        data.update({
            "sahriswiki": {
                "version": sahriswiki.__version__
            },
            "url":         self.url,
            "site":        self.site,
            "include":     self.include,
            "config":      self.config,
            "staticurl":   self.staticurl,
            "permissions": self._permissions(),
            "ctxnav":      chain(self._ctxnav(), data.get("ctxnav", [])),
            "metanav":     chain(self._metanav(), data.get("metanav", [])),
            "breadcrumbs": list(self._breadcrumbs(data.get("page", None))),
        })
        t = self.templates.load(template)
        return t.generate(**data).render("xhtml", doctype="xhtml")

    @handler("request", priority=1.0, target="web")
    def _on_request(self, request, response):
        self.request = request
        self.response = response

    @handler("databaseloaded")
    def _on_database_loaded(self):
        tables = self.dbm.engine.table_names()
        for Table, rows in schema.DATA:
            if Table.__tablename__ not in tables:
                self.dbm.session.begin()
                for row in rows:
                    self.dbm.session.add(Table(*row))
                self.dbm.session.commit()
