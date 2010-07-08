import os

from circuits import handler, BaseComponent

from genshi.template import TemplateLoader

from creoleparser import create_dialect, creole11_base, Parser

import macros
from sahriswiki import __version__

class Environment(BaseComponent):

    def __init__(self, opts, storage, search):
        super(Environment, self).__init__()

        self.opts = opts
        self.storage = storage
        self.search = search

        self.parser = Parser(create_dialect(creole11_base,
            macro_func=macros.dispatcher, wiki_links_base_url="/"),
            method="xhtml")

        self.templates = TemplateLoader(os.path.join(os.path.dirname(__file__),
            "templates"), auto_reload=True)

        self.macros = macros.loadMacros()

        self.stylesheets = []
        self.version =  __version__

        self.site = {
            "name": self.opts.name,
            "author": self.opts.author,
            "keywords": self.opts.keywords,
            "description": self.opts.description}

        self.request = None
        self.response = None

    def include(self, name):
        if name in self.storage:
            return self.parser.generate(self.storage.page_text(name),
                    environ=self)
        else:
            data = {"page": {"name": name}}
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
