# -*- coding: utf-8 -*-
# Module:   search
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Search and Indexing SUpport

...
"""

import re

from sqlalchemy import func, exists
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import Column, ForeignKey, Integer, Sequence, String

import schema
from i18n import _
from dbm import Base
from errors import NotFoundErr
from utils import external_link, extract_links

class Title(Base):

    __tablename__ = "titles"

    id = Column(Integer, Sequence("titles_id_seq"), primary_key=True)
    title = Column(String(50))

    def __init__(self, title):
        self.title = title

    def __repr__(self):
        return "<Title('%s')>" % self.title

class Word(Base):

    __tablename__ = "words"

    id = Column(Integer, Sequence("words_id_seq"), primary_key=True)
    word = Column(String(50), index=True)
    page = Column(Integer, ForeignKey("titles.title"), index=True)
    count = Column(Integer)

    def __init__(self, word, page, count):
        self.word = word
        self.page = page
        self.count = count

    def __repr__(self):
        return "<Word('%s', '%s', %d)>" % (self.word, self.page, self.count)

class Link(Base):

    __tablename__ = "links"

    id = Column(Integer, Sequence("links_id_seq"), primary_key=True)
    src = Column(Integer, ForeignKey("titles.title"), index=True)
    target = Column(Integer, ForeignKey("titles.title"), index=True)
    label = Column(String(50))
    number = Column(Integer)

    def __init__(self, src, target, label, number):
        self.src = src
        self.target = target
        self.label = label
        self.number = number

    def __repr__(self):
        return "<Link('%s', '%s', '%s', %d)>" % (self.src, self.target,
                self.label, self.number)

class WikiSearch(object):
    """
    Responsible for indexing words and links, for fast searching and
    backlinks. Uses a cache directory to store the index files.
    """

    word_pattern = re.compile(ur"""\w[-~&\w]+\w""", re.UNICODE)

    def __init__(self, db, lang, storage):
        self.db = db
        self.lang = lang
        self.storage = storage

        self.stop_words_re = re.compile(u'^('+u'|'.join(re.escape(_(
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
without would yet you your yours yourself yourselves""")).split())
+ur')$|.*\d.*', re.U|re.I|re.X)

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

    def title_id(self, title):
        try:
            return self.db.query(Title.id).filter(
                    Title.title==title).one().id
        except NoResultFound:
            self.db.add(Title(title))
            return self.db.query(Title.id).filter(
                    Title.title==title).one().id

    def update_words(self, title, text):
        title_id = self.title_id(title)
        self.db.query(Word).filter(Word.page==title_id).delete()
        if not text:
            return
        words = self.count_words(self.split_text(text))
        title_words = self.count_words(self.split_text(title))
        for word, count in title_words.iteritems():
            words[word] = words.get(word, 0) + count
        for word, count in words.iteritems():
            self.db.add(Word(word, title_id, count))

    def update_links(self, title, links_and_labels):
        title_id = self.title_id(title)
        self.db.query(Link).filter(Link.src==title_id).delete()
        for number, (link, label) in enumerate(links_and_labels):
            self.db.add(Link(title_id, link, label, number))

    def orphaned_pages(self):
        """Gives all pages with no links to them."""

        stmt = ~exists().where(Link.target==Title.title)
        orphaned = self.db.query(Title.title).\
                filter(stmt).\
                order_by(Title.title)
        for (title,) in orphaned:
            yield unicode(title)

    def wanted_pages(self):
        """Gives all pages that are linked to, but don't exist, together with
        the number of links."""

        stmt = ~exists().where(Title.title==Link.target)
        wanted = self.db.query(func.count(), Link.target).\
                filter(stmt).\
                group_by(Link.target).\
                order_by(-func.count())
        for refs, title, in wanted:
            title = unicode(title)
            if not external_link(title) and not title.startswith('+'):
                yield refs, title

    def page_backlinks(self, title):
        """Gives a list of pages linking to specified page."""

        backlinks = self.db.query(func.distinct(Title.title)).\
                join((Link, Link.src==Title.id)).\
                filter(Link.target==title).\
                order_by(Title.title)
        for (backlink,) in backlinks:
            yield unicode(backlink)

    def page_links(self, title):
        """Gives a list of links on specified page."""

        title_id = self.title_id(title)
        links = self.db.query(Link.target).\
                filter(Link.src==title_id).\
                order_by(Link.number)
        for link in links:
            yield unicode(link)

    def page_links_and_labels (self, title):
        title_id = self.title_id(title)
        links = self.db.query(Link.target, Link.label).\
                filter(Link.src==title_id).\
                order_by(Link.number)
        for link, label in links:
            yield unicode(link), unicode(label)

    def find(self, words):
        """Iterator of all pages containing the words, and their scores."""

        ranks = []
        for word in words:
            # Calculate popularity of each word.
            rank = self.db.query(func.sum(Word.count)).filter(
                    Word.word.like("%%%s%%" % word)).first()[0]
            # If any rank is 0, there will be no results anyways
            if not rank:
                return
            ranks.append((rank, word))
        ranks.sort()
        # Start with the least popular word. Get all pages that contain it.
        first_rank, first = ranks[0]
        rest = ranks[1:]
        first_counts = self.db.query(Word.page, Title.title,
                func.sum(Word.count)).\
                        filter(Word.word.like("%%%s%%" % first)).\
                        filter(Title.id==Word.page).\
                        group_by(Word.page)
        # Check for the rest of words
        for title_id, title, first_count in first_counts:
            # Score for the first word
            score = float(first_count)/first_rank
            for rank, word in rest:
                count = self.db.query(func.sum(Word.count)).\
                        filter(Word.page==title_id).\
                        filter(Word.word.like("%%%%s%%" % word)).\
                        first()
                if not count:
                    # If page misses any of the words, its score is 0
                    score = 0
                    break
                score += float(count)/rank
            if score > 0:
                yield int(100*score), unicode(title)

    def reindex_page(self, page, title, text=None):
        """Updates the content of the database, needs locks around."""

        if text is None:
            _get_text = getattr(page, '_get_text', lambda: u'')
            try:
                text = _get_text()
            except NotFoundErr:
                text = None
                title_id = self.title_id(title)
                if not list(self.page_backlinks(title)):
                    self.db.query(Title).filter(Title.id==title_id).delete()

        if text is not None:
            links = extract_links(text)
        else:
            links = []

        self.update_links(title, links)
        self.update_words(title, text or u'')

    def update_page(self, page, title, data=None, text=None):
        """Updates the index with new page content, for a single page."""

        if text is None and data is not None:
            text = unicode(data, self.storage.charset, 'replace')

        self.db.begin(subtransactions=True)

        try:
            self.set_last_revision(self.storage.repo_revision())
            self.reindex_page(page, title, text)
            self.db.commit()
        except:
            self.db.rollback()
            raise

    def reindex(self, environ, pages):
        """Updates specified pages in bulk."""

        self.db.begin(subtransactions=True)

        try:
            for title in pages:
                page = environ.get_page(title)
                self.reindex_page(page, title)
            self.db.commit()
        except Exception, e:
            self.db.rollback()
            raise

    def set_last_revision(self, rev):
        """Store the last indexed repository revision."""

        # We use % here because the sqlite3's substitiution doesn't work
        # We store revision 0 as 1, 1 as 2, etc. because 0 means "no revision"
        
        sysinfo = self.db.query(schema.System).get("search_revision")
        if sysinfo is None:
            self.db.add(schema.System("search_revision", (int(rev + 1))))
        else:
            sysinfo.value = int(rev + 1)

    def get_last_revision(self):
        """Retrieve the last indexed repository revision."""

        sysinfo = self.db.query(schema.System).get("search_revision")
        if sysinfo is None:
            return -1
        else:
            return int(sysinfo.value) - 1

    def update(self, environ):
        """Reindex al pages that changed since last indexing."""

        last_rev = self.get_last_revision()
        if last_rev == -1:
            changed = self.storage.all_pages()
        else:
            changed = self.storage.changed_since(last_rev)
        self.reindex(environ, changed)
        rev = self.storage.repo_revision()
        self.set_last_revision(rev)
