# -*- coding: utf-8 -*-

import os
import re
import sqlite3

def external_link(addr):
    """
    Decide whether a link is absolute or internal.

    >>> external_link("http://example.com")
    True
    >>> external_link("https://example.com")
    True
    >>> external_link("ftp://example.com")
    True
    >>> external_link("mailto:user@example.com")
    True
    >>> external_link("PageTitle")
    False
    >>> external_link(u"ąęśćUnicodePage")
    False

    """

    return (addr.startswith("http://")
            or addr.startswith("https://")
            or addr.startswith("ftp://")
            or addr.startswith("mailto:"))

def extract_links(text):
    links = re.compile(ur"\[\[(?P<link_target>([^|\]]|\][^|\]])+)"
            ur"(\|(?P<link_text>([^\]]|\][^\]])+))?\]\]")
    for m in links.finditer(text):
        if m.groupdict():
            d = m.groupdict()
            yield d["link_target"], d["link_text"] or ""

class WikiSearch(object):
    """
    Responsible for indexing words and links, for fast searching and
    backlinks. Uses a cache directory to store the index files.
    """

    word_pattern = re.compile(ur"""\w[-~&\w]+\w""", re.UNICODE)

    def __init__(self, path, storage):
        self.path = path
        self.storage = storage

        self.filename = os.path.join(self.path, "index.db")

        if not os.path.isdir(self.path):
            self.empty = True
            os.makedirs(self.path)
        elif not os.path.exists(self.filename):
            self.empty = True
        else:
            self.empty = False

        self.con = sqlite3.connect(self.filename)

        self.con.execute("CREATE TABLE IF NOT EXISTS titles "
                "(id INTEGER PRIMARY KEY, title VARCHAR);")
        self.con.execute("CREATE TABLE IF NOT EXISTS words "
                "(word VARCHAR, page INTEGER, count INTEGER);")
        self.con.execute("CREATE INDEX IF NOT EXISTS index1 "
                         "ON words (page);")
        self.con.execute("CREATE INDEX IF NOT EXISTS index2 "
                         "ON words (word);")
        self.con.execute("CREATE TABLE IF NOT EXISTS links "
                "(src INTEGER, target INTEGER, label VARCHAR, number INTEGER);")
        self.con.commit()
        self.stop_words_re = re.compile(u"^(" + u"|".join(re.escape(
u"""am ii iii per po re a about above
across after afterwards again against all almost alone along already also
although always am among ain amongst amoungst amount an and another any aren
anyhow anyone anything anyway anywhere are around as at back be became because
become becomes becoming been before beforehand behind being below beside
besides between beyond bill both but by can cannot cant con could couldnt
describe detail do done down due during each eg eight either eleven else etc
elsewhere empty enough even ever every everyone everything everywhere except
few fifteen fifty fill find fire first five for former formerly forty found
four from front full further get give go had has hasnt have he hence her here
hereafter hereby herein hereupon hers herself him himself his how however
hundred i ie if in inc indeed interest into is it its itself keep last latter
latterly least isn less made many may me meanwhile might mill mine more
moreover most mostly move much must my myself name namely neither never
nevertheless next nine no nobody none noone nor not nothing now nowhere of off
often on once one only onto or other others otherwise our ours ourselves out
over own per perhaps please pre put rather re same see seem seemed seeming
seems serious several she should show side since sincere six sixty so some
somehow someone something sometime sometimes somewhere still such take ten than
that the their theirs them themselves then thence there thereafter thereby
therefore therein thereupon these they thick thin third this those though three
through throughout thru thus to together too toward towards twelve twenty two
un under ve until up upon us very via was wasn we well were what whatever when
whence whenever where whereafter whereas whereby wherein whereupon wherever
whether which while whither who whoever whole whom whose why will with within
without would yet you your yours yourself yourselves""").split())
+ ur")$|.*\d.*", re.U | re.I | re.X)

        self.update()

    def split_text(self, text, stop=True):
        """Splits text into words, removing stop words"""

        for match in self.word_pattern.finditer(text):
            word = match.group(0)
            if not (stop and self.stop_words_re.match(word)):
                yield word.lower()

    def count_words(self, words):
        count = {}
        for word in words:
            count[word] = count.get(word, 0)+1
        return count

    def title_id(self, title, con):
        c = self.con.execute("SELECT id FROM titles WHERE title=?;", (title,))
        idents = c.fetchone()
        if idents is None:
            self.con.execute("INSERT INTO titles (title) VALUES (?);", (title,))
            c = self.con.execute("SELECT LAST_INSERT_ROWID();")
            idents = c.fetchone()
        return idents[0]

    def update_words(self, title, text, cursor):
        title_id = self.title_id(title, cursor)
        words = self.count_words(self.split_text(text))
        title_words = self.count_words(self.split_text(title))
        for word, count in title_words.iteritems():
            words[word] = words.get(word, 0) + count
        cursor.execute("DELETE FROM words WHERE page=?;", (title_id,))
        for word, count in words.iteritems():
            cursor.execute("INSERT INTO words VALUES (?, ?, ?);",
                             (word, title_id, count))

    def update_links(self, title, links_and_labels, cursor):
        title_id = self.title_id(title, cursor)
        cursor.execute("DELETE FROM links WHERE src=?;", (title_id,))
        for number, (link, label) in enumerate(links_and_labels):
            cursor.execute("INSERT INTO links VALUES (?, ?, ?, ?);",
                             (title_id, link, label, number))

    def orphaned_pages(self):
        """Gives all pages with no links to them."""

        con = self.con
        try:
            sql = ("SELECT title FROM titles "
                   "WHERE NOT EXISTS "
                   "(SELECT * FROM links WHERE target=title) "
                   "ORDER BY title;")
            for (title,) in con.execute(sql):
                yield unicode(title)
        finally:
            con.commit()

    def wanted_pages(self):
        """Gives all pages that are linked to, but don't exist, together with
        the number of links."""

        con = self.con
        try:
            sql = ("SELECT COUNT(*), target FROM links "
                   "WHERE NOT EXISTS "
                   "(SELECT * FROM titles WHERE target=title) "
                   "GROUP BY target ORDER BY -COUNT(*);")
            for (refs, db_title,) in con.execute(sql):
                title = unicode(db_title)
                if not external_link(title) and not title.startswith("+"):
                    yield refs, title
        finally:
            con.commit()

    def page_backlinks(self, title):
        con = self.con # sqlite3.connect(self.filename)
        try:
            sql = ("SELECT DISTINCT(titles.title) "
                   "FROM links, titles "
                   "WHERE links.target=? AND titles.id=links.src "
                   "ORDER BY titles.title;")
            for (backlink,) in con.execute(sql, (title,)):
                yield backlink
        finally:
            con.commit()

    def page_links(self, title):
        con = self.con # sqlite3.connect(self.filename)
        try:
            title_id = self.title_id(title, con)
            sql = "SELECT TARGET from links where src=? ORDER BY number;"
            for (link,) in con.execute(sql, (title_id,)):
                yield link
        finally:
            con.commit()

    def page_links_and_labels (self, title):
        con = self.con # sqlite3.connect(self.filename)
        try:
            title_id = self.title_id(title, con)
            sql = "SELECT target, label FROM links WHERE src=? ORDER BY number;"
            for link_and_label in con.execute(sql, (title_id,)):
                yield link_and_label
        finally:
            con.commit()

    def find(self, words):
        """Returns an iterator of all pages containing the words, and their
            scores."""

        con = self.con
        try:
            ranks = []
            for word in words:
                # Calculate popularity of each word.
                sql = "SELECT SUM(words.count) FROM words WHERE word LIKE ?;"
                rank = con.execute(sql, ("%%%s%%" % word,)).fetchone()[0]
                # If any rank is 0, there will be no results anyways
                if not rank:
                    return
                ranks.append((rank, word))
            ranks.sort()
            # Start with the least popular word. Get all pages that contain it.
            first_rank, first = ranks[0]
            rest = ranks[1:]
            sql = ("SELECT words.page, titles.title, SUM(words.count) "
                   "FROM words, titles "
                   "WHERE word LIKE ? AND titles.id=words.page "
                   "GROUP BY words.page;")
            first_counts = con.execute(sql, ("%%%s%%" % first,))
            # Check for the rest of words
            for title_id, title, first_count in first_counts:
                # Score for the first word
                score = float(first_count)/first_rank
                for rank, word in rest:
                    sql = ("SELECT SUM(count) FROM words "
                           "WHERE page=? AND word LIKE ?;")
                    count = con.execute(sql,
                        (title_id, "%%%s%%" % word)).fetchone()[0]
                    if not count:
                        # If page misses any of the words, its score is 0
                        score = 0
                        break
                    score += float(count)/rank
                if score > 0:
                    yield int(100*score), title
        finally:
            con.commit()

    def reindex_page(self, title, cursor, text=None):
        """Updates the content of the database, needs locks around."""

        mime = self.storage.page_mime(title)

        if not mime.startswith("text/"):
            self.update_words(title, "", cursor=cursor)
            return
        if text is None:
            text = self.storage.page_text(title) or u""

        if mime == "text/x-wiki":
            links = extract_links(text)
            self.update_links(title, links, cursor=cursor)

        self.update_words(title, text, cursor=cursor)

    def update_page(self, title, data=None, text=None):
        """Updates the index with new page content, for a single page."""

        if text is None and data is not None:
            text = unicode(data, self.storage.charset, "replace")
        cursor = self.con.cursor()
        try:
            self.set_last_revision(self.storage.repo_revision())
            self.reindex_page(title, cursor, text)
            self.con.commit()
        except:
            self.con.rollback()
            raise

    def reindex(self, pages):
        """Updates specified pages in bulk."""

        cursor = self.con.cursor()
        cursor.execute("BEGIN IMMEDIATE TRANSACTION;")
        try:
            for title in pages:
                self.reindex_page(title, cursor)
            self.con.commit()
            self.empty = False
        except:
            self.con.rollback()
            raise

    def set_last_revision(self, rev):
        """Store the last indexed repository revision."""

        # We use % here because the sqlite3's substitiution doesn't work
        # We store revision 0 as 1, 1 as 2, etc. because 0 means "no revision"
        self.con.execute("PRAGMA USER_VERSION=%d;" % (int(rev+1),))

    def get_last_revision(self):
        """Retrieve the last indexed repository revision."""

        con = self.con
        c = con.execute("PRAGMA USER_VERSION;")
        rev = c.fetchone()[0]
        # -1 means "no revision", 1 means revision 0, 2 means revision 1, etc.
        return rev-1

    def update(self):
        """Reindex al pages that changed since last indexing."""

        last_rev = self.get_last_revision()
        if last_rev == -1:
            changed = self.storage.all_pages()
        else:
            changed = self.storage.changed_since(last_rev)
        self.reindex(changed)
        rev = self.storage.repo_revision()
        self.set_last_revision(rev)
