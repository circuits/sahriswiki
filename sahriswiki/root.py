import os
import re
from operator import itemgetter
from difflib import unified_diff
from time import gmtime, strftime

from feedformatter import Feed

from mercurial.node import short

from circuits.web.controllers import expose, BaseController

from errors import ForbiddenErr, NotFoundErr

FIXLINES = re.compile("(\r[^\n])|(\r\n)")

class Root(BaseController):

    def __init__(self, environ):
        super(Root, self).__init__()

        self.environ = environ

        self.config = self.environ.config
        self.render = self.environ.render
        self.search = self.environ.search
        self.storage = self.environ.storage

    def _get_ctxnav(self, type="view"):
        if type in ("history", "index", "search"):
            yield ("Index",    self.url("/+search"))
            yield ("Orphaned", self.url("/+orphaned"))
            yield ("Wanted",   self.url("/+wanted"))

    @expose("index")
    def index(self, *args, **kwargs):
        if args:
            name = os.path.sep.join(args)
        else:
            for name in self.config.get("indexes"):
                if name in self.storage:
                    break

        page = self.environ.get_page(name)

        try:
            return page.view()
        except NotFoundErr:
            data = {"title": name}
            return self.render("notfound.html", **data)

    @expose("+download")
    def download(self, *args, **kwargs):
        name = os.path.sep.join(args) if args else self.config.get("index")
        page = self.environ.get_page(name)
        return page.download()

    @expose("+upload")
    def upload(self, *args, **kwargs):
        if self.config.get_bool("readonly"):
            raise ForbiddenErr("This wiki is in readonly mode.")

        action = kwargs.get("action", None)

        data = {
            "title": "Upload",
            "ctxnav": list(self._get_ctxnav("history")),
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
        if self.config.get_bool("readonly"):
            raise ForbiddenErr("This wiki is in readonly mode.")

        name = os.path.sep.join(args)
        page = self.environ.get_page(name)
        return page.edit()

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
            highlighted = "**%s**" % match.group(0)
            return regexp.sub(highlighted, text[min_pos:max_pos])

        def search(words):
            self.storage.reopen()
            self.search.update(self.environ)
            results = list(self.search.find(words))
            results.sort(key=itemgetter(0), reverse=True)
            for score, name in results:
                yield score, name, snippet(name, words)

        query = kwargs.get("q", None)
        if query is not None:
            query = query.strip()

        if not query:
            data = {
                "title": "Page Index",
                "ctxnav": list(self._get_ctxnav("history")),
            }
            if hasattr(self.storage, "all_pages_tree"):
                data["pages"] = sorted(self.storage.all_pages_tree())
            else:
                data["pages"] = sorted(self.storage.all_pages())

            return self.render("index.html", **data)

        words = tuple(self.search.split_text(query, stop=False))
        if not words:
            words = (query,)

        data = {
            "title": "Search",
            "query": " ".join(words),
            "results": list(search(words)),
            "ctxnav": list(self._get_ctxnav("history")),
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
            "ctxnav": list(self._get_ctxnav("history")),
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
            for rev, date, author, comment in self.storage.page_history(name):
                item = {}
                item["title"] = "%s by %s" % (name, author)
                item["link"] = self.request.url(name)
                item["description"] = comment
                item["pubDate"] = date
                item["guid"] = str(rev)

                feed.items.append(item)
        else:
            for name, rev, date, author, comment in self.storage.history():
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
            "ctxnav": list(self._get_ctxnav("history")),
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
            "ctxnav": list(self._get_ctxnav("history")),
        }

        return self.render("wanted.html", **data)

    @expose("+history")
    def history(self, *args, **kwargs):
        name = os.path.sep.join(args) or None
        if name:
            page = self.environ.get_page(name)
            return page.history()

        data = {
            "title": "Recent Changes",
            "history": self.storage.history(),
            "strftime": strftime,
            "gmtime": gmtime,
            "ctxnav": list(self._get_ctxnav("history")),
        }

        return self.render("recentchanges.html", **data)

    @expose("facicon.ico")
    def favicon(self, *args, **kwargs):
        if "favicon.ico" in self.storage:
            return self.download("favicon.ico")
        else:
            return self.serve_file(
                os.path.join(self.config.get("theme"), "favicon.ico")
            )

    @expose("robots.txt")
    def robots(self, *args, **kwargs):
        if "robots.txt" in self.storage:
            return self.download("robots.txt")

        self.response.headers["Content-Type"] = "text/plain"

        return "\r\n".join((
            "User-agent: *",
            "Disallow: /+*",
            "Disallow: /%2b*",
            "Disallow: /%2B*",
        ))

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
            "title": "diff -r %s -r %s %s" % (from_rev, to_rev, name),
            "name": self.name,
            "diff": diff,
        }

        return self.render("diff.html", **data)
