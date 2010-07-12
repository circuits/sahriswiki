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
from pagetypes import WikiPageWiki, WikiPageFile
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
    }

    def __init__(self, config):
        super(Environment, self).__init__()

        self.config = config

        self.storage = WikiStorage(
            self.config.get("data"),
            self.config.get("encoding")
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
            self.config.get("templates"),
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

        if name:
            try:
                page_class, mime = self.filename_map[name]
            except KeyError:
                mime = page_mime(name)
                major, minor = mime.split("/", 1)
                try:
                    page_class = self.mime_map[mime]
                except KeyError:
                    try:
                        plus_pos = minor.find("+")
                        if plus_pos>0:
                            minor_base = minor[plus_pos:]
                        else:
                            minor_base = ""
                        base_mime = "/".join([major, minor_base])
                        page_class = self.mime_map[base_mime]
                    except KeyError:
                        try:
                            page_class = self.mime_map[major]
                        except KeyError:
                                page_class = self.mime_map[""]
        else:
            page_class = WikiPage
            mime = ""
        return page_class(self, name, mime)

    def include(self, name, context=None):
        if name in self.storage:
            return self.parser.generate(self.storage.page_text(name),
                    environ=(self, context))
        else:
            data = {"name": name}
            t = self.templates.load("notfound.html")
            return t.generate(**data)

    def render(self, template, **data):
        data["environ"] = self
        t = self.templates.load(template)
        return t.generate(**data).render("xhtml", doctype="html")

    @handler("request", priority=1.0, target="web")
    def _on_request(self, request, response):
        self.request = request
        self.response = response
