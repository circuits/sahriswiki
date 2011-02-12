# Module:   pagetypes
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Page Types and Handling

...
"""

import os
import csv
from StringIO import StringIO
from operator import itemgetter
from time import strftime, gmtime

try:
    import docutils.core
    HAS_DOCUTILS = True
except ImportError:
    HAS_DOCUTILS = False

from genshi.input import HTML
from genshi.builder import tag
from genshi.core import Markup
from genshi.filters import HTMLSanitizer
from genshi.output import HTMLSerializer

from mercurial.node import short

from circuits.web.exceptions import Redirect
from circuits.web.tools import expires, serve_file

from utils import NEWLINES
from highlight import highlight
from errors import NotImplementedErr, UnsupportedMediaTypeErr

class WikiPage(object):
    """Everything needed for rendering a page."""

    def __init__(self, environ, name, mime):
        super(WikiPage, self).__init__()

        self.environ = environ
        self.name = name
        self.mime = mime

        self.request = self.environ.request
        self.response = self.environ.response

        self.url = self.request.url
        self.render = self.environ.render

        self.search = self.environ.search
        self.storage = self.environ.storage

    def _get_text(self):
        return self.storage.page_text(self.name)

    def _get_page_data(self):
        text = self._get_text()
        rev, node, date, author, comment = self.storage.page_meta(self.name)

        base = os.path.basename(self.name)
        parent = os.path.dirname(self.name)

        data = {
            "rev": rev,
            "base": base,
            "date": date,
            "text": text,
            "parent": parent,
            "author": author,
            "name": self.name,
            "comment": comment,
            "node": short(node),
        }

        if hasattr(self.storage, "page_parent"):
            data["parent"] = self.storage.page_parent(self.name)

        self.environ.page = data

        return data

    def download(self):
        path = self.storage._file_path(self.name)
        expires(self.request, self.response, 60*60*24*30, force=True)
        return serve_file(self.request, self.response, path, type=self.mime)

    def edit(self):
        raise NotImplementedErr()

    def history(self):
        history = list(self.storage.page_history(self.name))[:30]
        data = {
            "name": self.name,
            "title": "History of %s" % self.name,
            "history": history,
            "strftime": strftime,
            "gmtime": gmtime,
            "ctxnav": list(self.environ._ctxnav("history"))
        }

        return self.render("history.html", **data)

    def view(self):
        raise NotImplementedErr()

class WikiPageText(WikiPage):
    """Pages of mime type text/* use this for display."""

    def _render(self, text=None):
        if text is None:
            text = self._get_text()

        return tag.pre(text)

    def edit(self):
        if not self.request.kwargs:
            if self.name in self.storage:
                data = {"page": self._get_page_data()}
                return self.render("edit.html", **data)
            else:
                data = {"page": {"name": self.name, "text": ""}}
                return self.render("edit.html", **data)

        action = self.request.kwargs.get("action", None)
        comment = self.request.kwargs.get("comment", "")
        parent = self.request.kwargs.get("parent", None)
        text = self.request.kwargs.get("text", "")

        text = NEWLINES.sub("\n", text)

        if action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data = {
                "page": {"name": self.name, "text": text},
                "author": self.environ._user(),
                "comment": comment,
                "preview": True,
            }
            data["html"] = self._render(text)
            return self.render("edit.html", **data)
        elif action == "save":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.save_text(self.name, text, self.environ._user(),
                comment, parent=parent)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

    def view(self):
        data = {
            "page": self._get_page_data(),
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }
        data["html"] = self._render()
        return self.render("view.html", **data)

class WikiPageColorText(WikiPageText):
    """Text pages, but displayed colorized with pygments"""

    def view(self):
        data = {
            "page": self._get_page_data(),
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }

        data["html"] = highlight(data["page"]["text"], mime=self.mime)
        return self.render("view.html", **data)

class WikiPageWiki(WikiPageText):
    """Pages of with wiki markup use this for display."""

    def _render(self, text=None, data={}):
        if text is None:
            text = self._get_text()

        return self.environ.parser.generate(text, context="block",
                environ=(self.environ, data))

    def edit(self):
        if not self.request.kwargs:
            if self.name in self.storage:
                data = {"page": self._get_page_data()}
                return self.render("edit.html", **data)
            else:
                data = {"page": {"name": self.name, "text": ""}}
                return self.render("edit.html", **data)

        action = self.request.kwargs.get("action", None)
        comment = self.request.kwargs.get("comment", "")
        parent = self.request.kwargs.get("parent", None)
        text = self.request.kwargs.get("text", "")

        text = NEWLINES.sub("\n", text)

        if action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data = {
                "page": {"name": self.name, "text": text},
                "author": self.environ._user(),
                "comment": comment,
                "preview": True,
            }
            data["html"] = self._render(text, data)
            return self.render("edit.html", **data)
        elif action == "save":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.save_text(self.name, text, self.environ._user(),
                    comment, parent=parent)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

    def view(self):
        data = {
            "page": self._get_page_data(),
            "ctxnav": self.environ._ctxnav("view", self.name),
        }
        data["html"] = self._render(data=data)
        return self.render("view.html", **data)

class WikiPageFile(WikiPage):
    """Pages of all other mime types use this for display."""

class WikiPageImage(WikiPageFile):
    """Pages of mime type image/* use this for display."""

    def view(self):
        if self.name not in self.storage:
            data = {"name": self.name}
            self.storage.reopen()
            self.search.update(self.environ)
            name, _ = os.path.splitext(self.name)
            data["results"] = sorted(self.search.find((name,)),
                    key=itemgetter(0), reverse=True)[:5]
            return self.render("notfound.html", **data)

        data = {
            "title": self.name,
            "name": self.name,
            "html": tag.img(
                alt=self.name,
                src=self.url("/+download/%s" % self.name)
            ),
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }

        return self.render("view.html", **data)

class WikiPageCSV(WikiPageFile):
    """Display class for type text/csv."""

    def _render(self, text=None):
        if text is None:
            text = self._get_text()

        data = csv.reader(StringIO(text))

        rows = (tag.tr(tag.td(cell) for cell in row) for row in data)

        stream = tag.table(rows)

        return stream.generate()

    def edit(self):
        if not self.request.kwargs:
            if self.name in self.storage:
                data = {"page": self._get_page_data()}
                return self.render("edit.html", **data)
            else:
                data = {"page": {"name": self.name, "text": ""}}
                return self.render("edit.html", **data)

        action = self.request.kwargs.get("action", None)
        comment = self.request.kwargs.get("comment", "")
        parent = self.request.kwargs.get("parent", None)
        text = self.request.kwargs.get("text", "")

        text = NEWLINES.sub("\n", text)

        if action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data = {
                "page": {"name": self.name, "text": text},
                "html": self._render(),
                "author": self.environ._user(),
                "comment": comment,
                "preview": True,
            }
            return self.render("edit.html", **data)
        elif action == "save":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.save_text(self.name, text, self.environ._user(), comment,
                    parent=parent)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

    def view(self):
        data = {
            "page": self._get_page_data(),
            "html": self._render(),
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }
        return self.render("view.html", **data)

class WikiPageRST(WikiPageText):
    """
    Display ReStructured Text.
    """

    def _render(self, text=None):
        if text is None:
            text = self._get_text()

        SAFE_DOCUTILS = dict(file_insertion_enabled=False, raw_enabled=False)

        return Markup(docutils.core.publish_parts(text, writer_name="html",
            settings_overrides=SAFE_DOCUTILS)["html_body"])

    def edit(self):
        if not self.request.kwargs:
            if self.name in self.storage:
                data = {"page": self._get_page_data()}
                return self.render("edit.html", **data)
            else:
                data = {"page": {"name": self.name, "text": ""}}
                return self.render("edit.html", **data)

        action = self.request.kwargs.get("action", None)
        comment = self.request.kwargs.get("comment", "")
        parent = self.request.kwargs.get("parent", None)
        text = self.request.kwargs.get("text", "")

        text = NEWLINES.sub("\n", text)

        if action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data = {
                "page": {"name": self.name, "text": text},
                "html": self._render(text),
                "author": self.environ._user(),
                "comment": comment,
                "preview": True,
            }
            return self.render("edit.html", **data)
        elif action == "save":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.save_text(self.name, text, self.environ._user(),
                    comment, parent=parent)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

    def view(self):
        if not HAS_DOCUTILS:
            raise UnsupportedMediaTypeErr("No docutils support available")

        data = {
            "page": self._get_page_data(),
            "html": self._render(),
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }
        return self.render("view.html", **data)

class WikiPageHTML(WikiPageText):
    """Display HTML (genshi) templates"""

    def __init__(self, environ, name, mime):
        super(WikiPageHTML, self).__init__(environ, name, mime)

        self.sanitizer = HTMLSanitizer()
        self.serializer = HTMLSerializer()

    def _render(self, text=None):
        if text is None:
            text = self._get_text()

        return self.sanitizer(HTML(text))

    def edit(self):
        if not self.request.kwargs:
            if self.name in self.storage:
                data = {"page": self._get_page_data()}
                return self.render("edit.html", **data)
            else:
                data = {"page": {"name": self.name, "text": ""}}
                return self.render("edit.html", **data)

        action = self.request.kwargs.get("action", None)
        comment = self.request.kwargs.get("comment", "")
        parent = self.request.kwargs.get("parent", None)
        text = self.request.kwargs.get("text", "")

        text = NEWLINES.sub("\n", text)

        if action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data = {
                "page": {"name": self.name, "text": text},
                "author": self.environ._user(),
                "comment": comment,
                "preview": True,
            }
            data["html"] = self._render(text)
            return self.render("edit.html", **data)
        elif action == "save":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.save_text(self.name, text, self.environ._user(),
                comment, parent=parent)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

    def view(self):
        data = {
            "page": self._get_page_data(),
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }
        data["html"] = self._render()
        return self.render("view.html", **data)
