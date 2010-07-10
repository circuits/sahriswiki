import os
import re
from operator import itemgetter
from difflib import unified_diff
from time import gmtime, strftime

from feedformatter import Feed

from mercurial.node import short

from circuits.web.controllers import expose, BaseController

from errors import NotFoundErr

FIXLINES = re.compile("(\r[^\n])|(\r\n)")

class Root(BaseController):

    def __init__(self, environ):
        super(Root, self).__init__()

        self.environ = environ

        self.render = self.environ.render
        self.search = self.environ.search
        self.storage = self.environ.storage

    @expose("index")
    def index(self, *args, **kwargs):
        name = os.path.sep.join(args) if args else self.environ.opts.frontpage
        page = self.environ.get_page(name)
        try:
            return page.view()
        except NotFoundErr:
            data = {
                "actions": [],
                "page": {"name": name}
            }
            return self.render("notfound.html", **data)

    @expose("+download")
    def download(self, *args, **kwargs):
        name = os.path.sep.join(args) if args else self.environ.opts.frontpage
        page = self.environ.get_page(name)
        return page.download()

    @expose("+upload")
    def upload(self, *args, **kwargs):
        action = kwargs.get("action", None)

        data = {}

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
        name = os.path.sep.join(args)
        page = self.environ.get_page(name)
        return page.edit()

    @expose("+search")
    def search(self, *args, **kwargs):

        def snippet(name, words):
            """Extract a snippet of text for search results."""

            text = unicode(self.storage.open_page(name).read(), "utf-8",
                    "replace")
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
                "actions": [
                    (self.request.url("/+orphaned"),    "Orphaned"),
                    (self.request.url("/+wanted"),      "Wanted")
                ],
                "page": {"name": "Index"},
                "pages": sorted(self.storage.all_pages()),
            }
            return self.render("index.html", **data)

        words = tuple(self.search.split_text(query, stop=False))
        if not words:
            words = (query,)

        data = {
            "actions": [],
            "page": {"name": "Search"},
            "query": " ".join(words),
            "results": list(search(words)),
        }

        return self.render("search.html", **data)

    @expose("+backlinks")
    def backlinks(self, *args, **kwargs):
        name = os.path.sep.join(args)
        data = {
            "actions": [
                (self.request.url("/+search"),      "Index"),
                (self.request.url("/+orphaned"),    "Orphaned"),
                (self.request.url("/+wanted"),      "Wanted")
            ],
            "page": {"name": "BackLinks for \"%s\"" % name},
            "pages": sorted(self.search.page_backlinks(name), key=itemgetter(0))
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
            feed.feed["title"] = "%s :: %s" % (name, self.data["site"]["name"])
        else:
            feed.feed["title"] = self.data["site"]["name"]

        feed.feed["link"] = self.request.server.base
        feed.feed["author"] = self.data["site"]["author"]
        feed.feed["description"] = self.data["site"]["description"]

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
            for name, ver, date, rev, author, comment in self.storage.history():
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
        data = {
            "actions": [
                (self.request.url("/+search"),      "Index"),
                (self.request.url("/+orphaned"),    "Orphaned"),
                (self.request.url("/+wanted"),      "Wanted")
            ],
            "page": {"name": "Orphaned Pages"},
            "pages": sorted(self.search.orphaned_pages(), key=itemgetter(0))
        }
        return self.render("index.html", **data)

    @expose("+wanted")
    def wanted(self, *args, **kwargs):
        data = {
            "actions": [
                (self.request.url("/+search"),      "Index"),
                (self.request.url("/+orphaned"),    "Orphaned"),
                (self.request.url("/+wanted"),      "Wanted")
            ],
            "page": {"name": "Wanted Pages"},
            "pages": sorted(self.search.wanted_pages(),
                key=itemgetter(0), reverse=True)

        }
        return self.render("index.html", **data)

    @expose("+history")
    def history(self, *args, **kwargs):
        name = os.path.sep.join(args) or None
        if name:
            page = self.environ.get_page(name)
            return page.history()

        rev = kwargs.get("rev", None)

        lines = []
        out = lines.append

        title = "Recent Changes"
        out("= %s =" % title)
        for name, ver, date, rev, author, comment in self.storage.history():
            out(" * [[+history/%s?rev=%d|%s]] [[%s]]" % (name, ver,
                strftime("%Y-%m-%d", gmtime(date)), name))
            out("[ [[%s|%d]] ] by [[%s]]\\\\" % (
                self.url("/+hg/rev/%d" % rev), rev, author))
            out(comment)
        text = "\n".join(lines)

        actions = [("/+feed", "RSS 1.0"),
                ("/+feed?format=rss2", "RSS 2.0"),
                ("/+feed?format=atom", "Atom")]

        return self.render("view.html", title=title, text=text,
                actions=actions)

    @expose("robots.txt")
    def robots(self, *args, **kwargs):
        self.response.headers["Content-Type"] = "text/plain"
        if "robots.txt" in self.storage:
            return self.storage.page_text("robots.txt")

        s = []
        s.append("User-agent: *")
        s.append("Disallow: /+*")
        s.append("Disallow: /%2b*")
        s.append("Disallow: /%2B*")
        return "\r\n".join(s)
