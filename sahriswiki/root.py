# Module:   root
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Root Controller

...
"""

import os
import re
from urlparse import urlparse
from operator import itemgetter
from difflib import unified_diff
from time import gmtime, strftime

from genshi.core import Markup

from circuits.web.tools import check_auth, basic_auth
from circuits.web.controllers import expose, BaseController

import schema
from feedformatter import Feed
from highlight import highlight
from errors import ForbiddenErr, NotFoundErr

class Root(BaseController):

    def __init__(self, environ):
        super(Root, self).__init__()

        self.environ = environ

        self.config = self.environ.config
        self.render = self.environ.render
        self.search = self.environ.search
        self.storage = self.environ.storage

    @expose("index")
    def index(self, *args, **kwargs):
        if args:
            name = os.path.sep.join(args)
        else:
            for name in self.config.get("indexes"):
                if name in self.storage:
                    break
            if not name in self.storage:
                name = self.config.get("frontpage")

        page = self.environ.get_page(name)

        try:
            return page.view()
        except NotFoundErr:
            data = {"title": name}
            data["results"] = sorted(self.search.find((name,)),
                    key=itemgetter(0), reverse=True)[:5]
            if hasattr(self.storage, "page_parent"):
                data["parent"] = self.storage.page_parent(name)
            return self.render("notfound.html", **data)

    @expose("+download")
    def download(self, *args, **kwargs):
        name = os.path.sep.join(args) if args else self.config.get("index")
        page = self.environ.get_page(name)
        return page.download()

    @expose("+upload")
    def upload(self, *args, **kwargs):
        if not self.environ._login() and self.config.get("readonly"):
            raise ForbiddenErr("This wiki is in readonly mode.")

        action = kwargs.get("action", None)

        data = {
            "title": "Upload",
        }

        if action == "upload":
            file = kwargs.get("file", None)
            if file is not None:
                filename = file.filename
                filedata = file.value
                comment = kwargs.get("comment", "Uploaded file: %s" % filename)

                data["filename"] = filename

                author = self.cookie.get("username")
                if author:
                    author = author.value
                else:
                    author = self.request.headers.get("X-Forwarded-For",
                            self.request.remote.ip or "AnonymousUser")

                self.storage.reopen()
                self.storage.save_data(filename, filedata, author, comment)

        return self.render("upload.html", **data)

    @expose("+edit")
    def edit(self, *args, **kwargs):
        if not self.environ._login() and self.config.get("readonly"):
            raise ForbiddenErr("This wiki is in readonly mode.")

        name = os.path.sep.join(args)
        page = self.environ.get_page(name)
        return page.edit()

    @expose("+login")
    def login(self):
        db = self.environ.dbm.session
        users = dict(((user.username, user.password) \
                for user in db.query(schema.User).all()))
        realm = self.environ.config.get("name")

        if not check_auth(self.request, self.response, realm, users):
            return basic_auth(self.request, self.response, realm, users)

        if not self.request.login in users:
            return basic_auth(self.request, self.response, realm, users)

        self.request.session["login"] = self.request.login

        referer = self.request.headers.get("Referer", None)
        if referer:
            base = urlparse(self.url())
            link = urlparse(referer)
            if all([base[i] == link[i] for i in range(2)]):
                return self.redirect(referer)

        data = {
            "title": "Login",
            "html": Markup("Login successful.")
        }

        return self.render("view.html", **data)

    @expose("+logout")
    def logout(self):
        db = self.environ.dbm.session
        users = dict(((user.username, user.password) \
                for user in db.query(schema.User).all()))
        realm = self.environ.config.get("name")

        if "login" in self.request.session:
            del self.request.session["login"]

        if "Authorization" in self.request.headers:
            del self.request.headers["Authorization"]

        return basic_auth(self.request, self.response, realm, users)

    @expose("+about")
    def about(self):
        return self.render("about.html")

    @expose("+search")
    def search(self, *args, **kwargs):

        def snippet(name, words):
            """Extract a snippet of text for search results."""

            try:
                text = unicode(self.storage.open_page(name).read(),
                    "utf-8", errors="replace")
            except NotFoundErr:
                return u""

            regexp = re.compile(u"|".join(re.escape(w) for w in words),
                    re.U | re.I)
            match = regexp.search(text)
            if match is None:
                return u""
            position = match.start()
            min_pos = max(position - 60, 0)
            max_pos = min(position + 60, len(text))
            highlighted = "<span class=\"highlight\">%s</span>" % match.group(0)
            return regexp.sub(highlighted, text[min_pos:max_pos])

        def search(words):
            self.storage.reopen()
            self.search.update(self.environ)
            results = list(self.search.find(words))
            results.sort(key=itemgetter(0), reverse=True)
            for score, name in results:
                yield score, name, Markup(snippet(name, words))

        query = kwargs.get("q", None)
        if query is not None:
            query = query.strip()

        if not query:
            data = {
                "title": "Page Index",
                "ctxnav": self.environ._ctxnav("index"),
            }
            if hasattr(self.storage, "all_pages_tree"):
                data["pages"] = sorted(self.storage.all_pages_tree())
            else:
                data["pages"] = sorted(self.storage.all_pages())

            return self.render("index.html", **data)

        if query in self.storage:
            return self.redirect(query)

        words = tuple(self.search.split_text(query, stop=False))
        if not words:
            words = (query,)

        data = {
            "title": "Search results for \"%s\"" % query,
            "name": "Search",
            "query": query,
            "results": list(search(words)),
            "ctxnav": self.environ._ctxnav("search"),
        }

        return self.render("search.html", **data)

    @expose("+backlinks")
    def backlinks(self, *args, **kwargs):
        name = os.path.sep.join(args)

        self.storage.reopen()
        self.search.update(self.environ)

        data = {
            "title": "BackLinks for \"%s\"" % name,
            "pages": sorted(self.search.page_backlinks(name),
                key=itemgetter(0)),
            "ctxnav": self.environ._ctxnav("search"),
        }
        return self.render("index.html", **data)

    @expose("+feed")
    def feed(self, *args, **kwargs):
        name = os.path.sep.join(args) if args else None
        format = kwargs.get("format", "rss1")

        if not format in ("rss1", "rss2", "atom"):
            raise Exception("Invalid format %r" % format)

        feed = Feed()

        if name is not None:
            feed.feed["title"] = "%s :: %s" % (name, self.environ.site["name"])
        else:
            feed.feed["title"] = self.environ.site["name"]

        feed.feed["link"] = self.request.server.base
        feed.feed["author"] = self.environ.site["author"]
        feed.feed["description"] = self.environ.site["description"]

        if name is not None:
            history = list(self.storage.page_history(name))[:30]
            for rev, date, author, comment in history:
                item = {}
                item["title"] = "%s by %s" % (name, author)
                item["link"] = self.request.url(name)
                item["description"] = comment
                item["pubDate"] = date
                item["guid"] = str(rev)

                feed.items.append(item)
        else:
            history = list(self.storage.history())[:30]
            for name, rev, date, author, comment in history:
                item = {}
                item["title"] = "%s by %s" % (name, author)
                item["link"] = self.request.url(name)
                item["description"] = comment
                item["pubDate"] = date
                item["guid"] = str(rev)

                feed.items.append(item)

        self.response.headers["Content-Type"] = "application/xml"
        return getattr(feed, "format_%s_string" % format)()

    @expose("+orphaned")
    def orphaned(self, *args, **kwargs):
        self.storage.reopen()
        self.search.update(self.environ)

        data = {
            "title": "Orphaned Pages",
            "pages": sorted(self.search.orphaned_pages(), key=itemgetter(0)),
            "ctxnav": self.environ._ctxnav("index"),
        }

        return self.render("orphaned.html", **data)

    @expose("+wanted")
    def wanted(self, *args, **kwargs):
        self.storage.reopen()
        self.search.update(self.environ)

        data = {
            "title": "Wanted Pages",
            "pages": sorted(self.search.wanted_pages(),
                key=itemgetter(0), reverse=True),
            "ctxnav": self.environ._ctxnav("index"),
        }

        return self.render("wanted.html", **data)

    @expose("+history")
    def history(self, *args, **kwargs):
        name = os.path.sep.join(args) or None
        if name:
            page = self.environ.get_page(name)
            return page.history()

        history = list(self.storage.history())[:30]

        data = {
            "title": "Recent Changes",
            "history": history,
            "strftime": strftime,
            "gmtime": gmtime,
            "ctxnav": self.environ._ctxnav("history"),
        }

        return self.render("recentchanges.html", **data)

    @expose("facicon.ico")
    def favicon(self, *args, **kwargs):
        if "favicon.ico" in self.storage:
            return self.download("favicon.ico")
        else:
            return self.serve_file(
                os.path.join(self.config.get("theme"), "htdocs", "favicon.ico")
            )

    @expose("robots.txt")
    def robots(self, *args, **kwargs):
        if "robots.txt" in self.storage:
            return self.download("robots.txt")

        self.response.headers["Content-Type"] = "text/plain"

        return "\r\n".join((
            "User-agent: *",
            "Disallow: /+",
            "Disallow: /%2b",
            "Disallow: /%2B",
        ))

    @expose("+delete")
    def delete(self, *args, **kwargs):
        name = os.path.sep.join(args)

        if name not in self.storage:
            data = {"title": name}
            data["results"] = sorted(self.search.find((name,)),
                    key=itemgetter(0), reverse=True)[:5]
            if hasattr(self.storage, "page_parent"):
                data["parent"] = self.storage.page_parent(name)
            return self.render("notfound.html", **data)

        action = kwargs.get("action", None)

        if not action:
            data = {"title": name}
            return self.render("delete.html", **data)

        if action == "delete":
            comment = kwargs.get("comment", "")

            self.storage.reopen()
            self.search.update(self.environ)

            self.storage.delete_page(name, self.environ._user(), comment)
            self.search.update_page(self, name)

            data = {"success": True, "message": "Page deleted successfully."}
            return self.render("delete.html", **data)
        else:
            raise Exception("Invalid action %r" % action)

    @expose("+rename")
    def rename(self, *args, **kwargs):
        name = os.path.sep.join(args)

        if name not in self.storage:
            data = {"title": name}
            data["results"] = sorted(self.search.find((name,)),
                    key=itemgetter(0), reverse=True)[:5]
            if hasattr(self.storage, "page_parent"):
                data["parent"] = self.storage.page_parent(name)
            return self.render("notfound.html", **data)

        action = kwargs.get("action", None)

        if not action:
            data = {"title": name}
            return self.render("rename.html", **data)

        if action == "rename":
            newname = kwargs.get("name", "")
            if newname and newname not in self.storage:
                comment = kwargs.get("comment", "")

                self.storage.reopen()
                self.search.update(self.environ)

                user = self.environ._user()

                text = self.storage.page_text(name)
                self.storage.save_text(newname, text, user, comment)
                self.search.update_page(self, newname, text=text)

                self.storage.delete_page(name, user, comment)
                self.search.update_page(self, name)

                data = {
                    "success": True,
                    "message": "Page renamed successfully.",
                }
            elif newname in self.storage:
                data = {
                    "success": False,
                    "message": "%s already exists" % newname,
                }
            else:
                data = {
                    "success": False,
                    "message": "A new name is requried",
                }

            return self.render("rename.html", **data)
        else:
            raise Exception("Invalid action %r" % action)

    @expose("+diff")
    def diff(self, *args, **kwargs):
        name = os.path.sep.join(args)

        rev = kwargs["rev"]

        to_rev = int(rev)
        from_rev = to_rev - 1

        text = self.storage.revision_text(name, from_rev).split("\n")
        other = self.storage.revision_text(name, to_rev).split("\n")

        to_date = ""
        from_date = ""
        date_format = "%Y-%m-%dT%H:%M:%SZ"

        for history in self.storage.page_history(name):
            if history[0] == to_rev:
                to_date = history[1]
            elif history[0] == from_rev:
                from_date = history[1]

        if not from_date:
            from_date = to_date

        diff = "\n".join(unified_diff(text, other,
            "%s@%d" % (name, from_rev),
            "%s@%d" % (name, to_rev),
            strftime(date_format, gmtime(from_date)),
            strftime(date_format, gmtime(to_date))))

        data = {
            "title": "diff of %s from %s to %s" % (name, from_rev, to_rev),
            "diff": highlight(diff, lang="diff"),
        }

        return self.render("diff.html", **data)
