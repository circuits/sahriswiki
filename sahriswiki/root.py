import os
import re
from operator import itemgetter
from difflib import unified_diff
from time import gmtime, strftime

from feedformatter import Feed

from mercurial.node import short

from circuits.web.controllers import expose, BaseController

FIXLINES = re.compile("(\r[^\n])|(\r\n)")

class Root(BaseController):

    def __init__(self, environ):
        super(Root, self).__init__()

        self.environ = environ

        self.storage = self.environ.storage
        self.search = self.environ.search

    def render(self, template, **data):
        name = data.get("name", None)
        if name is not None:
            text = self.storage.page_text(name)
            rev, node, date, author, comment = self.storage.page_meta(name)

            page = {"name": name, "text": text, "rev": rev,
                    "node": short(node), "date": date, "author": author,
                    "comment": comment,
                    "url": self.url(name),
                    "feed": self.url("/+feed/%s" % name),
                    "backlinks": self.url("/+backlinks/%s" % name)}
        else:
            page = {"name": data.get("title", ""),
                    "text": data.get("text", "")}

        data["page"] = self.environ.page = page

        return self.environ.render(template, **data)

    @expose("index")
    def index(self, *args, **kwargs):
        name = os.path.sep.join(args) if args else self.environ.opts.frontpage

        if name in self.environ.storage:
            actions = [("/+edit/%s" % name, "Edit"),
                    ("/+history/%s" % name, "History")]
            return self.render("view.html", name=name, actions=actions)
        else:
            return self.render("notfound.html", title=name)

    @expose("+download")
    def download(self, *args, **kwargs):
        name = os.path.sep.join(args) if args else self.environ.opts.frontpage
        if name in self.storage:
            mime = self.storage.page_mime(name)
            self.response.headers["Content-Type"] = mime
            return self.storage.open_page(name)
        else:
            return self.notfound(name)

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
        if not kwargs:
            if name in self.environ.storage:
                return self.render("edit.html", name=name)
            else:
                return self.render("edit.html", title=name)

        author = self.cookie.get("username")
        if author:
            author = author.value
        else:
            author = self.request.headers.get("X-Forwarded-For",
                    self.request.remote.ip or "AnonymousUser")

        action = kwargs.get("action", None)
        comment = kwargs.get("comment", "")
        parent = kwargs.get("parent", None)
        text = kwargs.get("text", "")

        if text:
            text = "%s\n" % FIXLINES.sub("\n", text)
        else:
            action = "delete"

        if action == "delete":
            self.storage.reopen()
            self.search.update()

            self.storage.delete_page(name, author, comment)
            self.search.update_page(name, text=text)

            return self.redirect(self.url("/%s" % name))
        elif action == "cancel":
            return self.redirect(self.url("/%s" % name))
        elif action == "preview":
            return self.render("edit.html", title=name, text=text,
                    author=author, comment=comment, preview=True)
        elif action == "save":
            self.storage.reopen()
            self.search.update()

            self.storage.save_text(name, text, author, comment, parent=parent)
            self.search.update_page(name, text=text)

            return self.redirect(self.url("/%s" % name))
        else:
            raise Exception("Invalid action %r" % action)

    @expose("+search")
    def search(self, *args, **kwargs):
        def index():
            yield "= Page Index ="
            for name in sorted(self.storage.all_pages()):
                yield " * [[%s]]" % name

        def snippet(title, words):
            """Extract a snippet of text for search results."""

            text = unicode(self.storage.open_page(title).read(), "utf-8",
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
            yield "= Searching for '%s' =" % " ".join(words)
            self.storage.reopen()
            self.search.update()
            result = sorted(self.search.find(words), key=lambda x:-x[0])
            yield "%d page(s) containing words:" % len(result)
            for score, title in result:
                yield "* **[[%s]]** //(%d)// %s" % (title, score,
                        snippet(title, words))

        q = kwargs.get("q", None)

        if q is not None:
            query = q.strip()
        else:
            query = None

        actions = []

        if not query:
            text = "\n".join(index())
            title = "Page index"
            actions = [("/+orphaned", "Orphaned"), ("/+wanted", "Wanted")]
        else:
            words = tuple(self.search.split_text(query, stop=False))
            if not words:
                words = (query,)
            title = "Searching for '%s'" % " ".join(words)
            text = "\n".join(search(words))

        return self.render("view.html", itle="Search", text=text,
                actions=actions)

    @expose("+backlinks")
    def backlinks(self, *args, **kwargs):
        name = os.path.sep.join(args)

        def content():
            yield "= BackLinks for [[%s]] =" % name
            yield "Pages that contain a link to %s: " % name
            for link in self.search.page_backlinks(name):
                yield "* [[%s]]" % link

        self.storage.reopen()
        self.search.update()

        text = "\n".join(content())
        title = "BackLinks for %s" % name
        actions = [("/+search", "Index"),
                ("/+orphaned", "Orphaned"),
                ("/+wanted", "Wanted")]

        return self.render("view.html", title="BackLinks", text=text,
                actions=actions)

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
        lines = []
        out = lines.append

        title = "Orphaned Pages"
        out("= %s =" % title)

        pages = list(self.search.orphaned_pages())
        pages.sort()

        for name in pages:
            out(" * [[%s]]" % name)

        text = "\n".join(lines)
        actions = [("/+orphaned", "Orphaned"), ("/+wanted", "Wanted")]

        return self.render("view.html", title=title, text=text,
                actions=actions)

    @expose("+wanted")
    def wanted(self, *args, **kwargs):
        lines = []
        out = lines.append

        title = "Wanted Pages"
        out("= %s =" % title)

        pages = list(self.search.wanted_pages())
        pages.sort(key=itemgetter(0), reverse=True)

        for refs, name in pages:
            out(" * [[%s]] / [[+backlinks/%s]]  //%d references//" % (name,
                name, refs))

        text = "\n".join(lines)
        actions = [("/+orphaned", "Orphaned"), ("/+wanted", "Wanted")]

        return self.render("view.html", title=title, text=text,
                actions=actions)

    @expose("+history")
    def history(self, *args, **kwargs):
        page_name = os.path.sep.join(args) or ""
        rev = kwargs.get("rev", None)

        lines = []
        out = lines.append

        if page_name:
            if rev is not None:
                to_rev = int(rev)
                from_rev = to_rev - 1
                title = "History of \"%s\" from %d to %d" % (page_name,
                        from_rev, to_rev)
                out("= %s =" % title)

                text = self.storage.revision_text(page_name,
                        from_rev).split("\n")
                other = self.storage.revision_text(page_name,
                        to_rev).split("\n")

                to_date = ""
                from_date = ""
                date_format = "%Y-%m-%dT%H:%M:%SZ"

                for history in self.storage.page_history(page_name):
                    if history[0] == to_rev:
                        to_date = history[1]
                    elif history[0] == from_rev:
                        from_date = history[1]

                if not from_date:
                    from_date = to_date

                out("{{{")
                for line in unified_diff(text, other,
                        "%s@%d" % (page_name, from_rev),
                        "%s@%d" % (page_name, to_rev),
                        strftime(date_format, gmtime(from_date)),
                        strftime(date_format, gmtime(to_date))):
                    out(line.rstrip("\n"))
                out("}}}")
            else:
                title = "History of \"%s\"" % page_name
                out("= %s =" % title)
                for rev, date, author, comment in self.storage.page_history(
                        page_name):
                    out(" * [[+history/%s?rev=%d|%s]]" % (page_name, rev,
                        strftime("%Y-%m-%d", gmtime(date))))

                    out("[ [[%s|%d]] ] by [[%s]]\\\\" % (
                        self.url("/+hg/rev/%d" % rev), rev, author))
                    out(comment)
            text = "\n".join(lines)
        else:
            title = "Recent Changes"
            out("= %s =" % title)
            for name, ver, date, rev, author, comment in self.storage.history():
                out(" * [[+history/%s?rev=%d|%s]] [[%s]]" % (name, ver,
                    strftime("%Y-%m-%d", gmtime(date)), name))
                out("[ [[%s|%d]] ] by [[%s]]\\\\" % (
                    self.url("/+hg/rev/%d" % rev), rev, author))
                out(comment)
            text = "\n".join(lines)

        actions = [("/+feed/%s" % page_name or "", "RSS 1.0"),
                ("/+feed/%s?format=rss2" % page_name or "", "RSS 2.0"),
                ("/+feed/%s?format=atom" % page_name or "", "Atom")]

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
