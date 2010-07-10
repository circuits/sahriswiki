from mercurial.node import short

class WikiPage(object):
    """Everything needed for rendering a page."""

    def __init__(self, environ, name, mime):
        super(WikiPage, self).__init__()

        self.environ = environ
        self.name = name
        self.mime = mime

        # for now we just use the globals from environ object
        #self.get_url = self.request.get_url # FIXME
        #self.get_download_url = self.request.get_download_url # FIXME

        self.request = self.environ.request
        self.response = self.environ.response

        self.url = self.request.url
        self.render = self.environ.render

        self.search = self.environ.search
        self.storage = self.environ.storage

        #self.config = self.environ.config # TODO

    def view(self):
        return self.render("view.html")

    def edit(self):
        return self.render("edit.html")

    def download(self):
        return self.render("download.html")

class WikiPageText(WikiPage):
    """Pages of mime type text/* use this for display."""

class WikiPageColorText(WikiPageText):
    """Text pages, but displayed colorized with pygments"""

class WikiPageWiki(WikiPageColorText):
    """Pages of with wiki markup use this for display."""

    def view(self):
        data = {}
        data["actions"] = [
            ("/+edit/%s" % self.name, "Edit"),
            ("/+history/%s" % self.name, "History"),
        ]

        text = self.storage.page_text(self.name)
        rev, node, date, author, comment = self.storage.page_meta(self.name)

        data["page"] = self.environ.page = {
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

        return self.render("view.html", **data)

class WikiPageFile(WikiPage):
    """Pages of all other mime types use this for display."""

class WikiPageImage(WikiPageFile):
    """Pages of mime type image/* use this for display."""

class WikiPageCSV(WikiPageFile):
    """Display class for type text/csv."""

class WikiPageRST(WikiPageText):
    """
    Display ReStructured Text.
    """

class WikiPageBugs(WikiPageText):
    """
    Display class for type text/x-bugs
    Parse the ISSUES file in (roughly) format used by ciss
    """
