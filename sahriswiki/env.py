import os
from urllib import basejoin

from circuits import handler, BaseComponent

from genshi.template import TemplateLoader

from creoleparser import create_dialect, creole11_base, Parser

import macros
import sahriswiki
from utils import page_mime
from search import WikiSearch
from storage import WikiStorage
from storage import WikiSubdirectoryStorage
from storage import WikiSubdirectoryIndexesStorage
from pagetypes import WikiPageWiki, WikiPageFile, WikiPageHello
from pagetypes import WikiPageText, WikiPageHTML, WikiPageImage
from pagetypes import WikiPageColorText, WikiPageCSV, WikiPageRST

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
    }

    def __init__(self, config):
        super(Environment, self).__init__()

        self.config = config

        self.storage = WikiSubdirectoryIndexesStorage(
            self.config.get("data"),
            self.config.get("encoding"),
            indexes=self.config.get("indexes"),
        )

        self.search = WikiSearch(
            self.config.get("cache"),
            self.config.get("language"),
            self.storage
        )

        self.parser = Parser(
            create_dialect(
                creole11_base,
                macro_func=macros.dispatcher,
                wiki_links_base_url="/"
            ),
            method="xhtml"
        )

        self.templates = TemplateLoader((
            self.storage.path,
            os.path.join(self.config.get("theme"), "tpl"),
        ), auto_reload=True)

        self.macros = macros.loadMacros()

        self.stylesheets = []
        self.version = sahriswiki.__version__

        self.site = {
            "name": self.config.get("name"),
            "author": self.config.get("author"),
            "keywords": self.config.get("keywords"),
            "description": self.config.get("description")
        }

        self.request = None
        self.response = None

    def _get_metanav(self):
        yield ("Login",    self.url("/+login"))
        yield ("Register", self.url("/+register"))

    def url(self, *args):
        return self.request.url("/".join(args))

    def staticurl(self, url):
        base = self.config.get("static-baseurl")
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
            data = {"name": name}
            return self.templates.load("notfound.html").generate(**data)

    def render(self, template, **data):
        data["environ"] = self
        data["metanav"] = list(self._get_metanav())
        t = self.templates.load(template)
        return t.generate(**data).render("xhtml", doctype="html")

    @handler("request", priority=1.0, target="web")
    def _on_request(self, request, response):
        self.request = request
        self.response = response
