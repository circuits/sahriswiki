import csv
import docutils.core
from StringIO import StringIO
from time import strftime, gmtime

from genshi import Markup

from mercurial.node import short

from circuits.web.tools import serve_file
from circuits.web.exceptions import NotImplemented, Redirect

from utils import FIXLINES

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

    def download(self):
        raise NotImplemented()

    def edit(self):
        raise NotImplemented()

    def history(self):
        raise NotImplemented()

    def view(self):
        raise NotImplemented()

class WikiPageText(WikiPage):
    """Pages of mime type text/* use this for display."""

    def _get_text(self):
        return self.storage.page_text(self.name)

    def _get_page_data(self):
        text = self._get_text()
        rev, node, date, author, comment = self.storage.page_meta(self.name)

        data = {
            "rev": rev,
            "date": date,
            "text": text,
            "author": author,
            "name": self.name,
            "comment": comment,
            "node": short(node),
            "url": self.url(self.name),
            "feed": self.url("/+feed/%s" % self.name),
        }

        return data

    def download(self):
        path = self.storage._file_path(self.name)
        return serve_file(self.request, self.response, path, type=self.mime)

    def edit(self):
        data = {
            "actions": [],
        }

        if not self.request.kwargs:
            if self.name in self.storage:
                data["page"] = self._get_page_data()
                return self.render("edit_plain.html", **data)
            else:
                data["page"] = {"name": self.name, "text": ""}
                return self.render("edit_plain.html", **data)

        author = self.request.cookie.get("username")
        if author:
            author = author.value
        else:
            author = self.request.headers.get("X-Forwarded-For",
                    self.request.remote.ip or "AnonymousUser")

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

            self.storage.delete_page(self.name, author, comment)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        elif action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "save":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.save_text(self.name, text, author, comment,
                    parent=parent)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

    def history(self):
        data = {
            "actions": [
                (self.url("/+feed"),                "RSS 1.0"),
                (self.url("/+feed?format=rss2"),    "RSS 2.0"),
                (self.url("/+feed?format=atom"),    "Atom"),
            ],
            "title": "History of \"%s\"" % self.name,
            "page": {"name": self.name},
            "history": self.storage.page_history(self.name),
            "strftime": strftime,
            "gmtime": gmtime,
        }

        return self.render("history.html", **data)

    def view(self):
        data = {
            "actions": [
                (self.url("/+edit/%s" % self.name),     "Edit"),
                (self.url("/+download/%s" % self.name), "Download"),
                (self.url("/+history/%s" % self.name),  "History"),
            ],
            "page": self._get_page_data()
        }

        return self.render("view_plain.html", **data)

class WikiPageColorText(WikiPageText):
    """Text pages, but displayed colorized with pygments"""

class WikiPageWiki(WikiPageColorText):
    """Pages of with wiki markup use this for display."""

    def _get_text(self):
        return self.storage.page_text(self.name)

    def _get_page_data(self):
        text = self._get_text()
        rev, node, date, author, comment = self.storage.page_meta(self.name)

        data = {
            "rev": rev,
            "date": date,
            "text": text,
            "author": author,
            "name": self.name,
            "comment": comment,
            "node": short(node),
            "url": self.url(self.name),
            "feed": self.url("/+feed/%s" % self.name),
            "backlinks": self.url("/+backlinks/%s" % self.name),
        }

        self.environ.page = data

        return data

    def download(self):
        path = self.storage._file_path(self.name)
        return serve_file(self.request, self.response, path, type=self.mime)

    def edit(self):
        data = {
            "actions": [],
        }

        if not self.request.kwargs:
            if self.name in self.storage:
                data["page"] = self._get_page_data()
                return self.render("edit.html", **data)
            else:
                data["page"] = {"name": self.name, "text": ""}
                return self.render("edit.html", **data)

        author = self.request.cookie.get("username")
        if author:
            author = author.value
        else:
            author = self.request.headers.get("X-Forwarded-For",
                    self.request.remote.ip or "AnonymousUser")

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

            self.storage.delete_page(self.name, author, comment)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        elif action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data["page"] = {"name": self.name, "text": text}
            data["author"] = author
            data["comment"] = comment
            data["preview"] = True
            return self.render("edit.html", **data)
        elif action == "save":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.save_text(self.name, text, author, comment,
                    parent=parent)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

    def history(self):
        data = {
            "actions": [
                (self.url("/+feed"),                "RSS 1.0"),
                (self.url("/+feed?format=rss2"),    "RSS 2.0"),
                (self.url("/+feed?format=atom"),    "Atom"),
            ],
            "title": "History of \"%s\"" % self.name,
            "page": {"name": self.name},
            "history": self.storage.page_history(self.name),
            "strftime": strftime,
            "gmtime": gmtime,
        }

        return self.render("history.html", **data)

    def view(self):
        data = {
            "actions": [
                (self.url("/+edit/%s" % self.name),     "Edit"),
                (self.url("/+download/%s" % self.name), "Download"),
                (self.url("/+history/%s" % self.name),  "History"),
            ],
            "page": self._get_page_data()
        }

        return self.render("view.html", **data)

class WikiPageFile(WikiPage):
    """Pages of all other mime types use this for display."""

class WikiPageImage(WikiPageFile):
    """Pages of mime type image/* use this for display."""

    def download(self):
        path = self.storage._file_path(self.name)
        return serve_file(self.request, self.response, path, type=self.mime)

    def edit(self):
        data = {
            "actions": [],
        }

        if not self.request.kwargs:
            raise NotImplemented()

        author = self.request.cookie.get("username")
        if author:
            author = author.value
        else:
            author = self.request.headers.get("X-Forwarded-For",
                    self.request.remote.ip or "AnonymousUser")

        action = self.request.kwargs.get("action", None)

        if action == "delete":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.delete_page(self.name, author, "deleted")
            self.search.update_page(self, self.name, "")

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

    def view(self):
        if self.name not in self.storage:
            data = {
                "actions": [],
                "page": {"name": self.name}
            }
            return self.render("notfound.html", **data)

        data = {
            "actions": [
                (self.url("/+edit/%s?action=delete" % self.name),
                    "Delete"),
                (self.url("/+download/%s" % self.name),
                    "Download"),
                (self.url("/+upload"),
                    "Upload"),
            ],
            "image": {
                "url": self.url("/+download/%s" % self.name),
                "alt": self.name,
            }
        }

        return self.render("view_image.html", **data)

class WikiPageCSV(WikiPageFile):
    """Display class for type text/csv."""

    def _get_text(self):
        return self.storage.page_text(self.name)

    def _get_page_data(self):
        text = self._get_text()
        rev, node, date, author, comment = self.storage.page_meta(self.name)

        data = {
            "rev": rev,
            "date": date,
            "text": text,
            "author": author,
            "name": self.name,
            "comment": comment,
            "node": short(node),
            "url": self.url(self.name),
            "feed": self.url("/+feed/%s" % self.name),
        }

        return data

    def download(self):
        path = self.storage._file_path(self.name)
        return serve_file(self.request, self.response, path, type=self.mime)

    def edit(self):
        data = {
            "actions": [],
        }

        if not self.request.kwargs:
            if self.name in self.storage:
                data["page"] = self._get_page_data()
                return self.render("edit_csv.html", **data)
            else:
                data["page"] = {"name": self.name, "text": ""}
                return self.render("edit_csv.html", **data)

        author = self.request.cookie.get("username")
        if author:
            author = author.value
        else:
            author = self.request.headers.get("X-Forwarded-For",
                    self.request.remote.ip or "AnonymousUser")

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

            self.storage.delete_page(self.name, author, comment)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        elif action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data["page"] = {"name": self.name, "text": text}
            data["rows"] = csv.reader(StringIO(text))
            data["author"] = author
            data["comment"] = comment
            data["preview"] = True
            return self.render("edit_csv.html", **data)
        elif action == "save":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.save_text(self.name, text, author, comment,
                    parent=parent)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

    def history(self):
        data = {
            "actions": [
                (self.url("/+feed"),                "RSS 1.0"),
                (self.url("/+feed?format=rss2"),    "RSS 2.0"),
                (self.url("/+feed?format=atom"),    "Atom"),
            ],
            "title": "History of \"%s\"" % self.name,
            "page": {"name": self.name},
            "history": self.storage.page_history(self.name),
            "strftime": strftime,
            "gmtime": gmtime,
        }

        return self.render("history.html", **data)

    def view(self):
        data = {
            "actions": [
                (self.url("/+edit/%s" % self.name),     "Edit"),
                (self.url("/+download/%s" % self.name), "Download"),
                (self.url("/+history/%s" % self.name),  "History"),
            ],
            "page": self._get_page_data()
        }

        data["page"]["rows"] = csv.reader(
                StringIO(data["page"]["text"]))

        return self.render("view_csv.html", **data)

class WikiPageRST(WikiPageText):
    """
    Display ReStructured Text.
    """

    def _get_text(self):
        return self.storage.page_text(self.name)

    def _get_page_data(self):
        text = self._get_text()
        rev, node, date, author, comment = self.storage.page_meta(self.name)

        data = {
            "rev": rev,
            "date": date,
            "text": text,
            "author": author,
            "name": self.name,
            "comment": comment,
            "node": short(node),
            "url": self.url(self.name),
            "feed": self.url("/+feed/%s" % self.name),
        }

        return data

    def _render(self, text=None):
        if text is None:
            text = self._get_text()

        SAFE_DOCUTILS = dict(file_insertion_enabled=False, raw_enabled=False)

        return Markup(publish_parts(text, writer_name="html",
            settings_overrides=SAFE_DOCUTILS)["html_body"])

    def download(self):
        path = self.storage._file_path(self.name)
        return serve_file(self.request, self.response, path, type=self.mime)

    def edit(self):
        data = {
            "actions": [],
        }

        if not self.request.kwargs:
            if self.name in self.storage:
                data["page"] = self._get_page_data()
                return self.render("edit_rst.html", **data)
            else:
                data["page"] = {"name": self.name, "text": ""}
                return self.render("edit_rst.html", **data)

        author = self.request.cookie.get("username")
        if author:
            author = author.value
        else:
            author = self.request.headers.get("X-Forwarded-For",
                    self.request.remote.ip or "AnonymousUser")

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

            self.storage.delete_page(self.name, author, comment)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        elif action == "cancel":
            raise Redirect(self.url("/%s" % self.name))
        elif action == "preview":
            data["page"] = {"name": self.name, "text": text}
            data["output"] = self._render(text)
            data["author"] = author
            data["comment"] = comment
            data["preview"] = True
            return self.render("edit_rst.html", **data)
        elif action == "save":
            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.save_text(self.name, text, author, comment,
                    parent=parent)
            self.search.update_page(self, self.name, text=text)

            raise Redirect(self.url("/%s" % self.name))
        else:
            raise Exception("Invalid action %r" % action)

    def history(self):
        data = {
            "actions": [
                (self.url("/+feed"),                "RSS 1.0"),
                (self.url("/+feed?format=rss2"),    "RSS 2.0"),
                (self.url("/+feed?format=atom"),    "Atom"),
            ],
            "title": "History of \"%s\"" % self.name,
            "page": {"name": self.name},
            "history": self.storage.page_history(self.name),
            "strftime": strftime,
            "gmtime": gmtime,
        }

        return self.render("history.html", **data)

    def view(self):
        data = {
            "actions": [
                (self.url("/+edit/%s" % self.name),     "Edit"),
                (self.url("/+download/%s" % self.name), "Download"),
                (self.url("/+history/%s" % self.name),  "History"),
            ],
            "page": self._get_page_data()
        }

        data["page"]["output"] = self._renger()

        return self.render("view_csv.html", **data)

class WikiPageBugs(WikiPageText):
    """
    Display class for type text/x-bugs
    Parse the ISSUES file in (roughly) format used by ciss
    """
