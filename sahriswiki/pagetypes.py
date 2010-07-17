# Module:   pagetypes
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Page Types and Handling

...
"""

import os
import csv
from urlparse import urlparse
from StringIO import StringIO
from time import strftime, gmtime

try:
    import docutils.core
    HAS_DOCUTILS = True
except ImportError:
    HAS_DOCUTILS = False

from genshi import Markup
from genshi.template import Template

from mercurial.node import short

from circuits.web.tools import serve_file
from circuits.web.exceptions import Redirect
from circuits.web.tools import check_auth, basic_auth

from utils import FIXLINES
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
        return serve_file(self.request, self.response, path, type=self.mime)

    def edit(self):
        raise NotImplemented()

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

class WikiPageLogin(WikiPage):
    """Pages of mime type +login/* use this for display."""

    def view(self):
        users = self.environ.users
        realm = self.environ.config.get("name")

        if not check_auth(self.request, self.response, realm, users):
            return basic_auth(self.request, self.response, realm, users)

        if not self.request.login in self.environ.users:
            return basic_auth(self.request, self.response, realm, users)

        self.request.session["login"] = self.request.login

        referer = self.request.headers.get("Referer", None)
        if referer:
            base = urlparse(self.url())
            link = urlparse(referer)
            if all([base[i] == link[i] for i in range(2)]):
                raise Redirect(referer)

        data = {
            "title": "Login",
            "html": Markup("Login successful.")
        }

        return self.render("view.html", **data)

class WikiPageLogout(WikiPage):
    """Pages of mime type +logout/* use this for display."""

    def view(self):
        users = self.environ.users
        realm = self.environ.config.get("name")

        if "login" in self.request.session:
            del self.request.session["login"]

        if "Authorization" in self.request.headers:
            del self.request.headers["Authorization"]

        return basic_auth(self.request, self.response, realm, users)

class WikiPageHello(WikiPage):
    """Pages of mime type +hello/* use this for display."""

    def view(self):
        data = {
            "title": "Hello",
            "html": Markup("Hello World!"),
        }
        return self.render("view.html", **data)

class WikiPageAbout(WikiPage):
    """Pages of mime type +about/* use this for display."""

    def view(self):
        return self.render("about.html", title="About SahrisWiki")
        
class WikiPageText(WikiPage):
    """Pages of mime type text/* use this for display."""

    def edit(self):
        if not self.request.kwargs:
            if self.name in self.storage:
                data = {"page": self._get_page_data()}
                return self.render("edit_plain.html", **data)
            else:
                data = {"page": {"name": self.name, "text": ""}}
                return self.render("edit_plain.html", **data)

        action = self.request.kwargs.get("action", None)
        comment = self.request.kwargs.get("comment", "")
        parent = self.request.kwargs.get("parent", None)
        text = self.request.kwargs.get("text", "")

        if text:
            text = FIXLINES.sub("\n", text)
        else:
            action = "delete"

        if action == "delete":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.delete_page(self.name, self.environ._user(), comment)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        elif action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
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
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }
        return self.render("view_plain.html", **data)

class WikiPageColorText(WikiPageText):
    """Text pages, but displayed colorized with pygments"""

class WikiPageWiki(WikiPageColorText):
    """Pages of with wiki markup use this for display."""

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

        if text:
            text = FIXLINES.sub("\n", text)
        else:
            action = "delete"

        if action == "delete":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.delete_page(self.name, self.environ._user(), comment)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        elif action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data = {
                "page": {"name": self.name, "text": text},
                "author": self.environ._user(),
                "comment": comment,
                "preview": True,
            }
            data["html"] = self.environ.parser.generate(
                data["page"]["text"], environ=(self.environ, data))
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
            "ctxnav": list(self.environ._ctxnav("view", self.name))
        }
        data["html"] = self.environ.parser.generate(
            data["page"]["text"], environ=(self.environ, data))
        return self.render("view.html", **data)

class WikiPageFile(WikiPage):
    """Pages of all other mime types use this for display."""

class WikiPageImage(WikiPageFile):
    """Pages of mime type image/* use this for display."""

    def edit(self):
        if not self.request.kwargs:
            raise NotImplemented()

        action = self.request.kwargs.get("action", None)

        if action == "delete":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.delete_page(self.name, self.environ._user(), "deleted")
            self.search.update_page(self, self.name, "")

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

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
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }

        return self.render("view_image.html", **data)

class WikiPageCSV(WikiPageFile):
    """Display class for type text/csv."""

    def edit(self):
        if not self.request.kwargs:
            if self.name in self.storage:
                data = {"page": self._get_page_data()}
                return self.render("edit_csv.html", **data)
            else:
                data = {"page": {"name": self.name, "text": ""}}
                return self.render("edit_csv.html", **data)

        action = self.request.kwargs.get("action", None)
        comment = self.request.kwargs.get("comment", "")
        parent = self.request.kwargs.get("parent", None)
        text = self.request.kwargs.get("text", "")

        if text:
            text = FIXLINES.sub("\n", text)
        else:
            action = "delete"

        if action == "delete":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.delete_page(self.name, self.environ._user(), comment)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        elif action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data = {
                "page": {"name": self.name, "text": text},
                "rows": csv.reader(StringIO(text)),
                "author": self.environ._user(),
                "comment": comment,
                "preview": True,
            }
            return self.render("edit_csv.html", **data)
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
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }
        data["rows"] = csv.reader(StringIO(data["page"]["text"]))
        return self.render("view_csv.html", **data)

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
                return self.render("edit_rst.html", **data)
            else:
                data = {"page": {"name": self.name, "text": ""}}
                return self.render("edit_rst.html", **data)

        action = self.request.kwargs.get("action", None)
        comment = self.request.kwargs.get("comment", "")
        parent = self.request.kwargs.get("parent", None)
        text = self.request.kwargs.get("text", "")

        if text:
            text = FIXLINES.sub("\n", text)
        else:
            action = "delete"

        if action == "delete":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.delete_page(self.name, self.environ._user(), comment)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        elif action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data = {
                "page": {"name": self.name, "text": text},
                "output": self._render(text),
                "author": self.environ._user(),
                "comment": comment,
                "preview": True,
            }
            return self.render("edit_rst.html", **data)
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
        if not HAS_DOCUTILS:
            raise UnsupportedMediaTypeErr("No docutils support available")

        data = {
            "page": self._get_page_data(),
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }
        data["output"] = self._render()
        return self.render("view_rst.html", **data)

class WikiPageHTML(WikiPageColorText):
    """Display HTML (genshi) templates"""

    def edit(self):
        if not self.request.kwargs:
            if self.name in self.storage:
                data = {"page": self._get_page_data()}
                return self.render("edit_html.html", **data)
            else:
                data = {"page": {"name": self.name, "text": ""}}
                return self.render("edit_html.html", **data)

        action = self.request.kwargs.get("action", None)
        comment = self.request.kwargs.get("comment", "")
        parent = self.request.kwargs.get("parent", None)
        text = self.request.kwargs.get("text", "")

        if text:
            text = FIXLINES.sub("\n", text)
        else:
            action = "delete"

        if action == "delete":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.delete_page(self.name, self.environ._user(), comment)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        elif action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data = {
                "page": {"name": self.name, "text": text},
                "author": self.environ._user(),
                "comment": comment,
                "preview": True,
                "html": Template(text).render(**data),
            }
            return self.render("edit_html.html", **data)
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
            "ctxnav": list(self.environ._ctxnav("view", self.name)),
        }
        data["html"] = Markup(self.render(self.name, **data))
        return self.render("view_html.html", **data)
