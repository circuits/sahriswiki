#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""SahrisWiki - The logical wiki!

SahrisWiki is a new WikiWiki Engine designed for simplicity, flexibility
and ease of use.
"""

import os
import re
import sys
import signal
import sqlite3
import tempfile
import optparse
import mimetypes
from operator import itemgetter
from difflib import unified_diff
from time import gmtime, strftime
from inspect import getmembers, isclass

try:
    import psyco
except ImportError:
    psyco = None

os.environ["HGENCODING"] = "utf-8"
os.environ["HGMERGE"] = "internal:merge"

import mercurial.hg
import mercurial.ui
import mercurial.util
import mercurial.revlog
from mercurial.node import short
from mercurial.hgweb import hgweb

from genshi.template import TemplateLoader

from feedformatter import Feed

from creoleparser import create_dialect, creole11_base, Parser

from circuits.app import Daemon
from circuits.net.pollers import Select, Poll
from circuits import Component, Manager, Debugger

from circuits.web.wsgi import Gateway
from circuits.web.tools import validate_etags
from circuits.web.utils import url_quote, url_unquote
from circuits.web import expose, url, Server, Controller, Logger, Static

try:
    from circuits.net.pollers import EPoll
except ImportError:
    EPoll = None

import macros
from plugins import BasePlugin

FIXLINES = re.compile("(\r[^\n])|(\r\n)")

def __version__():
    version = None
    if os.path.isdir(".hg"):
        f = os.popen("hg identify")
        ident = f.read()[:-1]
        if not f.close() and ident:
            ids = ident.split(' ', 1)
            version = ids.pop(0)
            if version[-1] == '+':
                version = version[:-1]
            if version.isalnum() and ids:
                for tag in ids[0].split('/'):
                    # is a tag is suitable as a version number?
                    if re.match(r'^(\d+\.)+[\w.-]+$', tag):
                        version = tag
                        break
    return version or "Unknown"

USAGE = "%prog [options]"
VERSION = "%prog v" + __version__()

def parse_options():
    """parse_options() -> opts, args

    Parse the command-line options given returning both
    the parsed options and arguments.
    """

    parser = optparse.OptionParser(usage=USAGE, version=VERSION)

    parser.add_option("-b", "--bind",
            action="store", type="string", default="0.0.0.0:8000",
            dest="bind",
            help="Bind to address:[port]")

    parser.add_option("-d", "--data-dir",
            action="store", type="string", default="wiki",
            dest="data",
            help="Location of data directory")

    parser.add_option("-c", "--cache-dir",
            action="store", type="string", default="cache",
            dest="cache",
            help="Location of cache directory")

    parser.add_option("", "--name",
            action="store", type="string", default="SahrisWiki",
            dest="name",
            help="Name")

    parser.add_option("", "--author",
            action="store", type="string", default="",
            dest="author",
            help="Author")

    parser.add_option("", "--keywords",
            action="store", type="string", default="",
            dest="keywords",
            help="Keywords")

    parser.add_option("", "--description",
            action="store", type="string", default=__doc__.split("\n")[0],
            dest="description",
            help="Description")

    parser.add_option("-f", "--front-page",
            action="store", type="string", default="FrontPage",
            dest="frontpage",
            help="Set main front page")

    parser.add_option("-e", "--encoding",
            action="store", type="string", default="utf-8",
            dest="encoding",
            help="Set encoding to read and write pages")

    parser.add_option("-r", "--read-only",
            action="store_true", default=False,
            dest="readonly",
            help="Set wiki in read-only mode")

    parser.add_option("-p", "--plugins",
            action="store", default="plugins",
            dest="plugins",
            help="Set directory where plugins are located")

    parser.add_option("", "--jit",
            action="store_true", default=False,
            dest="jit",
            help="Use python HIT (psyco)")

    parser.add_option("", "--multi-processing",
            action="store_true", default=False,
            dest="mp",
            help="Start in multiprocessing mode")

    parser.add_option("", "--poller",
            action="store", type="string", default="select",
            dest="poller",
            help="Specify type of poller to use")

    parser.add_option("", "--debug",
            action="store_true", default=False,
            dest="debug",
            help="Enable debug mode")

    parser.add_option("", "--pid-file",
            action="store", default=None,
            dest="pidfile",
            help="Write process id to pidfile")

    parser.add_option("", "--daemon",
            action="store_true", default=False,
            dest="daemon",
            help="Daemonize (fork into the background)")

    opts, args = parser.parse_args()

    return opts, args

def locked_repo(func):
    """A decorator for locking the repository when calling a method."""

    def new_func(self, *args, **kwargs):
        """Wrap the original function in locks."""

        wlock = self.repo.wlock()
        lock = self.repo.lock()
        try:
            func(self, *args, **kwargs)
        finally:
            lock.release()
            wlock.release()

    return new_func

def page_mime(addr):
    mime, encoding = mimetypes.guess_type(addr, strict=False)
    if encoding:
        mime = 'archive/%s' % encoding
    if mime is None:
        mime = 'text/x-wiki'
    return mime

def extract_links(text):
    links = re.compile(ur"\[\[(?P<link_target>([^|\]]|\][^|\]])+)"
            ur"(\|(?P<link_text>([^\]]|\][^\]])+))?\]\]")
    for m in links.finditer(text):
        if m.groupdict():
            d = m.groupdict()
            yield d["link_target"], d["link_text"] or ""

def external_link(addr):
    """
    Decide whether a link is absolute or internal.

    >>> external_link('http://example.com')
    True
    >>> external_link('https://example.com')
    True
    >>> external_link('ftp://example.com')
    True
    >>> external_link('mailto:user@example.com')
    True
    >>> external_link('PageTitle')
    False
    >>> external_link(u'ąęśćUnicodePage')
    False

    """

    return (addr.startswith('http://')
            or addr.startswith('https://')
            or addr.startswith('ftp://')
            or addr.startswith('mailto:'))

class WikiStorage(object):
    """
    Provides means of storing wiki pages and keeping track of their
    change history, using Mercurial repository as the storage method.
    """

    def __init__(self, path, charset=None):
        """
        Takes the path to the directory where the pages are to be kept.
        If the directory doen't exist, it will be created. If it's inside
        a Mercurial repository, that repository will be used, otherwise
        a new repository will be created in it.
        """

        self.charset = charset or 'utf-8'
        self.path = path
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        self.repo_path = self._find_repo_path(self.path)
        try:
            self.ui = mercurial.ui.ui(report_untrusted=False,
                                      interactive=False, quiet=True)
        except TypeError:
            # Mercurial 1.3 changed the way we setup the ui object.
            self.ui = mercurial.ui.ui()
            self.ui.quiet = True
            self.ui._report_untrusted = False
            self.ui.setconfig('ui', 'interactive', False)
        if self.repo_path is None:
            self.repo_path = self.path
            create = True
        else:
            create = False
        self.repo_prefix = self.path[len(self.repo_path):].strip('/')
        self.repo = mercurial.hg.repository(self.ui, self.repo_path,
                                            create=create)

    def reopen(self):
        """Close and reopen the repo, to make sure we are up to date."""

        self.repo = mercurial.hg.repository(self.ui, self.repo_path)


    def _find_repo_path(self, path):
        """Go up the directory tree looking for a repository."""

        while not os.path.isdir(os.path.join(path, ".hg")):
            old_path, path = path, os.path.dirname(path)
            if path == old_path:
                return None
        return path

    def _file_path(self, title):
        return os.path.join(self.path, url_quote(title, safe=''))

    def _title_to_file(self, title):
        return os.path.join(self.repo_prefix,
                            url_quote(title, safe=''))

    def _file_to_title(self, filename):
        assert filename.startswith(self.repo_prefix)
        name = filename[len(self.repo_prefix):].strip('/')
        return url_unquote(name)

    def __contains__(self, title):
        return os.path.exists(self._file_path(title))

    def __iter__(self):
        return self.all_pages()

    def merge_changes(self, changectx, repo_file, text, user, parent):
        """Commits and merges conflicting changes in the repository."""

        tip_node = changectx.node()
        filectx = changectx[repo_file].filectx(parent)
        parent_node = filectx.changectx().node()

        self.repo.dirstate.setparents(parent_node)
        node = self._commit([repo_file], text, user)

        partial = lambda filename: repo_file == filename
        try:
            unresolved = mercurial.merge.update(self.repo, tip_node,
                                                True, False, partial)
        except mercurial.util.Abort:
            unresolved = 1, 1, 1, 1
        msg = u'merge of edit conflict'
        if unresolved[3]:
            msg = u'forced merge of edit conflict'
            try:
                mercurial.merge.update(self.repo, tip_node, True, True,
                                       partial)
            except mercurial.util.Abort:
                msg = u'failed merge of edit conflict'
        self.repo.dirstate.setparents(tip_node, node)
        # Mercurial 1.1 and later need updating the merge state
        try:
            mercurial.merge.mergestate(self.repo).mark(repo_file, "r")
        except (AttributeError, KeyError):
            pass
        return msg

    @locked_repo
    def save_file(self, title, file_name, author=u'', comment=u'', parent=None):
        """Save an existing file as specified page."""

        user = author.encode('utf-8') or u'anon'.encode('utf-8')
        text = comment.encode('utf-8') or u'comment'.encode('utf-8')
        repo_file = self._title_to_file(title)
        file_path = self._file_path(title)
        mercurial.util.rename(file_name, file_path)
        changectx = self._changectx()

        try:
            filectx_tip = changectx[repo_file]
            current_page_ver = (filectx_tip.filerev(),
                    short(filectx_tip.node()))
        except mercurial.revlog.LookupError:
            self.repo.add([repo_file])
            current_page_ver = ()

        if parent is not None and parent not in current_page_ver:
            msg = self.merge_changes(changectx, repo_file, text, user, parent)
            user = '<wiki>'
            text = msg.encode('utf-8')
        self._commit([repo_file], text, user)


    def _commit(self, files, text, user):
        try:
            return self.repo.commit(files=files, text=text, user=user,
                                    force=True, empty_ok=True)
        except TypeError:
            # Mercurial 1.3 doesn't accept empty_ok or files parameter
            match = mercurial.match.exact(self.repo_path, '', list(files))
            return self.repo.commit(match=match, text=text, user=user,
                                    force=True)


    def save_data(self, title, data, author=u'', comment=u'', parent=None):
        """Save data as specified page."""

        try:
            temp_path = tempfile.mkdtemp(dir=self.path)
            file_path = os.path.join(temp_path, 'saved')
            f = open(file_path, "wb")
            f.write(data)
            f.close()
            self.save_file(title, file_path, author, comment, parent)
        finally:
            try:
                os.unlink(file_path)
            except OSError:
                pass
            try:
                os.rmdir(temp_path)
            except OSError:
                pass

    def save_text(self, title, text, author=u'', comment=u'', parent=None):
        """Save text as specified page, encoded to charset."""

        data = text.encode(self.charset)
        self.save_data(title, data, author, comment, parent)

    def page_text(self, title):
        """Read unicode text of a page."""

        page = self.open_page(title)
        if page:
            data = page.read()
            text = unicode(data, self.charset, 'replace')
            return text
        else:
            return None

    def page_lines(self, page):
        for data in page:
            yield unicode(data, self.charset, 'replace')

    @locked_repo
    def delete_page(self, title, author=u'', comment=u''):
        user = author.encode('utf-8') or 'anon'
        text = comment.encode('utf-8') or 'deleted'
        repo_file = self._title_to_file(title)
        file_path = self._file_path(title)
        try:
            os.unlink(file_path)
        except OSError:
            pass
        self.repo.remove([repo_file])
        self._commit([repo_file], text, user)

    def open_page(self, title):
        try:
            return open(self._file_path(title), "rb")
        except IOError:
            return None

    def page_file_meta(self, title):
        """Get page's inode number, size and last modification time."""

        try:
            (st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size,
             st_atime, st_mtime, st_ctime) = os.stat(self._file_path(title))
        except OSError:
            return 0, 0, 0
        return st_ino, st_size, st_mtime

    def page_meta(self, title):
        """Get page's revision, date, last editor and his edit comment."""

        filectx_tip = self._find_filectx(title)
        if filectx_tip is None:
            return None
        rev = filectx_tip.filerev()
        node = filectx_tip.node()
        filectx = filectx_tip.filectx(rev)
        date = filectx.date()[0]
        author = unicode(filectx.user(), "utf-8",
                         'replace').split('<')[0].strip()
        comment = unicode(filectx.description(), "utf-8", 'replace')
        return rev, node, date, author, comment

    def repo_revision(self):
        return self._changectx().rev()

    def repo_node(self):
        return self._changectx().node()

    def page_mime(self, title):
        """Guess page's mime type ased on corresponding file name."""

        file_path = self._file_path(title)
        return page_mime(file_path)

    def _changectx(self):
        """Get the changectx of the tip."""
        try:
            # This is for Mercurial 1.0
            return self.repo.changectx()
        except TypeError:
            # Mercurial 1.3 (and possibly earlier) needs an argument
            return self.repo.changectx('tip')

    def _find_filectx(self, title):
        """Find the last revision in which the file existed."""

        repo_file = self._title_to_file(title)
        changectx = self._changectx()
        stack = [changectx]
        while repo_file not in changectx:
            if not stack:
                return None
            changectx = stack.pop()
            for parent in changectx.parents():
                if parent != changectx:
                    stack.append(parent)
        return changectx[repo_file]

    def page_history(self, title):
        """Iterate over the page's history."""

        filectx_tip = self._find_filectx(title)
        if filectx_tip is None:
            return
        maxrev = filectx_tip.filerev()
        minrev = 0
        for rev in range(maxrev, minrev-1, -1):
            filectx = filectx_tip.filectx(rev)
            date = filectx.date()[0]
            author = unicode(filectx.user(), "utf-8",
                             'replace').split('<')[0].strip()
            comment = unicode(filectx.description(), "utf-8", 'replace')
            yield rev, date, author, comment

    def page_revision(self, title, rev):
        """Get unicode contents of specified revision of the page."""

        filectx_tip = self._find_filectx(title)
        if filectx_tip is None:
            return None
        try:
            data = filectx_tip.filectx(rev).data()
        except IndexError:
            return None
        return data

    def revision_text(self, title, rev):
        data = self.page_revision(title, rev)
        text = unicode(data, self.charset, 'replace')
        return text

    def history(self):
        """Iterate over the history of entire wiki."""

        changectx = self._changectx()
        maxrev = changectx.rev()
        minrev = 0
        for wiki_rev in range(maxrev, minrev-1, -1):
            change = self.repo.changectx(wiki_rev)
            date = change.date()[0]
            author = unicode(change.user(), "utf-8",
                             'replace').split('<')[0].strip()
            comment = unicode(change.description(), "utf-8", 'replace')
            for repo_file in change.files():
                if repo_file.startswith(self.repo_prefix):
                    title = self._file_to_title(repo_file)
                    try:
                        version = change[repo_file].filerev()
                    except mercurial.revlog.LookupError:
                        version = -1
                    yield title, version, date, wiki_rev, author, comment

    def all_pages(self):
        """Iterate over the titles of all pages in the wiki."""

        for filename in os.listdir(self.path):
            if (os.path.isfile(os.path.join(self.path, filename))
                and not filename.startswith('.')):
                yield url_unquote(filename)

    def changed_since(self, rev):
        """Return all pages that changed since specified repository revision."""

        last = self.repo.lookup(int(rev))
        current = self.repo.lookup('tip')
        status = self.repo.status(current, last)
        modified, added, removed, deleted, unknown, ignored, clean = status
        for filename in modified+added+removed+deleted:
            if filename.startswith(self.repo_prefix):
                yield self._file_to_title(filename)

class WikiSearch(object):
    """
    Responsible for indexing words and links, for fast searching and
    backlinks. Uses a cache directory to store the index files.
    """

    word_pattern = re.compile(ur"""\w[-~&\w]+\w""", re.UNICODE)

    def __init__(self, cache_path, storage):
        self.path = cache_path
        self.storage = storage
        self.filename = os.path.join(cache_path, 'index.db')
        if not os.path.isdir(self.path):
            self.empty = True
            os.makedirs(self.path)
        elif not os.path.exists(self.filename):
            self.empty = True
        else:
            self.empty = False

        self.con = sqlite3.connect(self.filename)

        self.con.execute('CREATE TABLE IF NOT EXISTS titles '
                '(id INTEGER PRIMARY KEY, title VARCHAR);')
        self.con.execute('CREATE TABLE IF NOT EXISTS words '
                '(word VARCHAR, page INTEGER, count INTEGER);')
        self.con.execute('CREATE INDEX IF NOT EXISTS index1 '
                         'ON words (page);')
        self.con.execute('CREATE INDEX IF NOT EXISTS index2 '
                         'ON words (word);')
        self.con.execute('CREATE TABLE IF NOT EXISTS links '
                '(src INTEGER, target INTEGER, label VARCHAR, number INTEGER);')
        self.con.commit()
        self.stop_words_re = re.compile(u'^('+u'|'.join(re.escape(
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
+ur')$|.*\d.*', re.U|re.I|re.X)
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
        c = con.execute('SELECT id FROM titles WHERE title=?;', (title,))
        idents = c.fetchone()
        if idents is None:
            con.execute('INSERT INTO titles (title) VALUES (?);', (title,))
            c = con.execute('SELECT LAST_INSERT_ROWID();')
            idents = c.fetchone()
        return idents[0]

    def update_words(self, title, text, cursor):
        title_id = self.title_id(title, cursor)
        words = self.count_words(self.split_text(text))
        title_words = self.count_words(self.split_text(title))
        for word, count in title_words.iteritems():
            words[word] = words.get(word, 0) + count
        cursor.execute('DELETE FROM words WHERE page=?;', (title_id,))
        for word, count in words.iteritems():
            cursor.execute('INSERT INTO words VALUES (?, ?, ?);',
                             (word, title_id, count))

    def update_links(self, title, links_and_labels, cursor):
        title_id = self.title_id(title, cursor)
        cursor.execute('DELETE FROM links WHERE src=?;', (title_id,))
        for number, (link, label) in enumerate(links_and_labels):
            cursor.execute('INSERT INTO links VALUES (?, ?, ?, ?);',
                             (title_id, link, label, number))

    def orphaned_pages(self):
        """Gives all pages with no links to them."""

        con = self.con
        try:
            sql = ('SELECT title FROM titles '
                   'WHERE NOT EXISTS '
                   '(SELECT * FROM links WHERE target=title) '
                   'ORDER BY title;')
            for (title,) in con.execute(sql):
                yield unicode(title)
        finally:
            con.commit()

    def wanted_pages(self):
        """Gives all pages that are linked to, but don't exist, together with
        the number of links."""

        con = self.con
        try:
            sql = ('SELECT COUNT(*), target FROM links '
                   'WHERE NOT EXISTS '
                   '(SELECT * FROM titles WHERE target=title) '
                   'GROUP BY target ORDER BY -COUNT(*);')
            for (refs, db_title,) in con.execute(sql):
                title = unicode(db_title)
                if not external_link(title) and not title.startswith('+'):
                    yield refs, title
        finally:
            con.commit()

    def page_backlinks(self, title):
        con = self.con # sqlite3.connect(self.filename)
        try:
            sql = ('SELECT DISTINCT(titles.title) '
                   'FROM links, titles '
                   'WHERE links.target=? AND titles.id=links.src '
                   'ORDER BY titles.title;')
            for (backlink,) in con.execute(sql, (title,)):
                yield backlink
        finally:
            con.commit()

    def page_links(self, title):
        con = self.con # sqlite3.connect(self.filename)
        try:
            title_id = self.title_id(title, con)
            sql = 'SELECT TARGET from links where src=? ORDER BY number;'
            for (link,) in con.execute(sql, (title_id,)):
                yield link
        finally:
            con.commit()

    def page_links_and_labels (self, title):
        con = self.con # sqlite3.connect(self.filename)
        try:
            title_id = self.title_id(title, con)
            sql = 'SELECT target, label FROM links WHERE src=? ORDER BY number;'
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
                sql = 'SELECT SUM(words.count) FROM words WHERE word LIKE ?;'
                rank = con.execute(sql, ('%%%s%%' % word,)).fetchone()[0]
                # If any rank is 0, there will be no results anyways
                if not rank:
                    return
                ranks.append((rank, word))
            ranks.sort()
            # Start with the least popular word. Get all pages that contain it.
            first_rank, first = ranks[0]
            rest = ranks[1:]
            sql = ('SELECT words.page, titles.title, SUM(words.count) '
                   'FROM words, titles '
                   'WHERE word LIKE ? AND titles.id=words.page '
                   'GROUP BY words.page;')
            first_counts = con.execute(sql, ('%%%s%%' % first,))
            # Check for the rest of words
            for title_id, title, first_count in first_counts:
                # Score for the first word
                score = float(first_count)/first_rank
                for rank, word in rest:
                    sql = ('SELECT SUM(count) FROM words '
                           'WHERE page=? AND word LIKE ?;')
                    count = con.execute(sql,
                        (title_id, '%%%s%%' % word)).fetchone()[0]
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
        if not mime.startswith('text/'):
            self.update_words(title, '', cursor=cursor)
            return
        if text is None:
            text = self.storage.page_text(title) or u""
        if mime == 'text/x-wiki':
            links = extract_links(text)
            self.update_links(title, links, cursor=cursor)
        self.update_words(title, text, cursor=cursor)

    def update_page(self, title, data=None, text=None):
        """Updates the index with new page content, for a single page."""

        if text is None and data is not None:
            text = unicode(data, self.storage.charset, 'replace')
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
        cursor.execute('BEGIN IMMEDIATE TRANSACTION;')
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
        self.con.execute('PRAGMA USER_VERSION=%d;' % (int(rev+1),))

    def get_last_revision(self):
        """Retrieve the last indexed repository revision."""

        con = self.con
        c = con.execute('PRAGMA USER_VERSION;')
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

def safe__import__(moduleName, globals=globals(),
        locals=locals(), fromlist=[]):
    """Safe imports: rollback after a failed import.

    Initially inspired from the RollbackImporter in PyUnit,
    but it's now much simpler and works better for our needs.

    See http://pyunit.sourceforge.net/notes/reloading.html
    """

    alreadyImported = sys.modules.copy()
    try:
        return __import__(moduleName, globals, locals, fromlist)
    except Exception, e:
        raise
        for name in sys.modules.copy():
            if not name in alreadyImported:
                del (sys.modules[name])

class PluginManager(Component):

    def __init__(self, opts, storage, search):
        super(PluginManager, self).__init__()

        self.opts = opts
        self.storage = storage
        self.search = search

    def _loadPlugins(self, path):
        sys.path.append(path)
        package = os.path.basename(path)
        safe__import__(package, globals(), locals())

        for filename in os.listdir(path):
            if not os.path.isfile(os.path.join(path, filename)):
                continue
            elif not os.path.splitext(filename)[1] == ".py":
                continue
            elif filename == "__init__.py":
                continue

            module = os.path.splitext(filename)[0]
            self._loadPlugin(package, module)

    def _loadPlugin(self, package, module):
        m = safe__import__("%s.%s" % (package, module), globals(), locals())
        p1 = lambda x: isclass(x) and issubclass(x, BasePlugin)
        p2 = lambda x: x is not BasePlugin
        predicate = lambda x: p1(x) and p2(x)
        plugins = getmembers(m, predicate)

        for name, Plugin in plugins:
            o = Plugin(self, self.opts, self.storage, self.search)
            o.register(self)

    def started(self, component, mode):
        self._loadPlugins(os.path.abspath(self.opts.plugins))

class Tools(Component):

    def __init__(self, opts, storage, search):
        super(Tools, self).__init__()
        self.opts = opts
        self.storage = storage
        self.search = search

    def signal(self, sig, stack):
        if os.name == "posix" and sig == signal.SIGHUP:
            self.storage.reopen()

class Root(Controller):

    def __init__(self, opts, storage, search):
        super(Root, self).__init__()

        self.opts = opts
        self.storage = storage
        self.search = search

        self.parser = Parser(create_dialect(creole11_base,
            macro_func=macros.dispatcher, wiki_links_base_url="/"),
            method="xhtml")

        self.loader = TemplateLoader(os.path.join(os.path.dirname(__file__),
            "templates"), auto_reload=True)

        self.environ = {
                "opts": self.opts,
                "parser": self.parser,
                "search": self.search,
                "storage": self.storage,
                "macros": macros.loadMacros()}

        self.data = {
                "url": self.url,
                "stylesheets": [],
                "parser": self.parser,
                "version": __version__(),
                "include": self._include,
                "site": {
                    "name": self.opts.name,
                    "author": self.opts.author,
                    "keywords": self.opts.keywords,
                    "description": self.opts.description}}

    def _include(self, name, environ=None):
        if name in self.storage:
            return self.parser.generate(self.storage.page_text(name),
                    environ=environ)
        else:
            return self.parser.generate(
                    self.storage.page_text("NotFound") or "Page Not Found!",
                    environ=environ)

    def _render(self, template, name, **kwargs):
        data = self.data.copy()
        data.update(kwargs)
        environ = self.environ.copy()

        if name is not None:
            if name in self.storage:
                text = self.storage.page_text(name)
                rev, node, date, author, comment = self.storage.page_meta(name)

                self.response.headers.add_header("ETag", short(node))
                response = validate_etags(self.request, self.response)
                if response:
                    return response

                page = {"name": name, "text": text, "rev": rev,
                        "node": short(node), "date": date, "author": author,
                        "comment": comment,
                        "url": self.url(name),
                        "feed": self.url("/+feed/%s" % name)}
            else:
                if template == "view.html":
                    text = self.storage.page_text("NotFound") or ""
                else:
                    text = ""
                page = {"name": name, "text": text}
        else:
            page = {"name": kwargs.get("title", ""),
                    "text": kwargs.get("text", "")}

        data["request"] = environ["request"] = self.request
        data["page"] = environ["page"] = page
        data["environ"] = environ

        t = self.loader.load(template)
        return t.generate(**data).render("xhtml", doctype="html")

    def index(self, *args, **kwargs):
        node = short(self.storage.repo_node())
        self.response.headers.add_header("ETag", node)
        response = validate_etags(self.request, self.response)
        if response:
            return response

        name = "/".join(args) if args else self.opts.frontpage
        actions = [("/+edit/%s" % name, "Edit"),
                ("/+history/%s" % name, "History"),
                ("/+backlinks/%s" % name, "BackLinks")]
        return self._render("view.html", name, actions=actions)

    @expose("+download")
    def download(self, *args, **kwargs):
        node = short(self.storage.repo_node())
        self.response.headers.add_header("ETag", node)
        response = validate_etags(self.request, self.response)
        if response:
            return response

        name = "/".join(args) if args else self.opts.frontpage
        if name in self.storage:
            mime = self.storage.page_mime(name)
            self.response.headers["Content-Type"] = mime
            return self.storage.open_page(name)
        else:
            return self.notfound(name)

    @expose("+upload")
    def upload(self, *args, **kwargs):
        if not kwargs:
            node = short(self.storage.repo_node())
            self.response.headers.add_header("ETag", node)
            response = validate_etags(self.request, self.response)
            if response:
                return response

        action = kwargs.get("action", None)

        data = {}
        data["actions"] = []

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

        return self._render("upload.html", None, **data)

    @expose("+edit")
    def edit(self, *args, **kwargs):
        if not kwargs:
            node = short(self.storage.repo_node())
            self.response.headers.add_header("ETag", node)
            response = validate_etags(self.request, self.response)
            if response:
                return response

        name = "/".join(args)
        if not kwargs:
            return self._render("edit.html", name, actions=[])

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
            return self._render("edit.html", None, title=name, text=text,
                    author=author, comment=comment, preview=True, actions=[])
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
        node = short(self.storage.repo_node())
        self.response.headers.add_header("ETag", node)
        response = validate_etags(self.request, self.response)
        if response:
            return response

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

        return self._render("view.html", None,
                text=text, title="Search", actions=actions)

    @expose("+backlinks")
    def backlinks(self, *args, **kwargs):
        node = short(self.storage.repo_node())
        self.response.headers.add_header("ETag", node)
        response = validate_etags(self.request, self.response)
        if response:
            return response

        if args:
            name = "/".join(args)
        else:
            name = kwargs.get("name", None)

        node = short(self.storage.repo_node())
        self.response.headers.add_header("ETag", node)
        response = validate_etags(self.request, self.response)
        if response:
            return response

        def content():
            yield "= Backlinks for [[%s]] =" % name
            yield "Pages that contain a link to %s: " % name
            for link in self.search.page_backlinks(name):
                yield "* [[%s]]" % link

        self.storage.reopen()
        self.search.update()

        text = "\n".join(content())
        title = "Backlinks for %s" % name

        return self._render("view.html", None,
                text=text, title="BackLinks", actions=[])

    @expose("+feed")
    def feed(self, *args, **kwargs):
        node = short(self.storage.repo_node())
        self.response.headers.add_header("ETag", node)
        response = validate_etags(self.request, self.response)
        if response:
            return response

        name = "/".join(args) if args else None
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
        node = short(self.storage.repo_node())
        self.response.headers.add_header("ETag", node)
        response = validate_etags(self.request, self.response)
        if response:
            return response

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

        return self._render("view.html", None,
                text=text, title=title, actions=actions)

    @expose("+wanted")
    def wanted(self, *args, **kwargs):
        node = short(self.storage.repo_node())
        self.response.headers.add_header("ETag", node)
        response = validate_etags(self.request, self.response)
        if response:
            return response

        lines = []
        out = lines.append

        title = "Wanted Pages"
        out("= %s =" % title)

        pages = list(self.search.wanted_pages())
        pages.sort(key=itemgetter(0), reverse=True)

        for refs, name in pages:
            out(" * [[%s]] //%d references//" % (name, refs))

        text = "\n".join(lines)
        actions = [("/+orphaned", "Orphaned"), ("/+wanted", "Wanted")]

        return self._render("view.html", None,
                text=text, title=title, actions=actions)

    @expose("+history")
    def history(self, *args, **kwargs):
        node = short(self.storage.repo_node())
        self.response.headers.add_header("ETag", node)
        response = validate_etags(self.request, self.response)
        if response:
            return response

        page_name = "/".join(args) or ""
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
                        url(self.request, "/+hg/rev/%d" % rev), rev, author))
                    out(comment)
            text = "\n".join(lines)
        else:
            title = "Recent Changes"
            out("= %s =" % title)
            for name, ver, date, rev, author, comment in self.storage.history():
                out(" * [[+history/%s?rev=%d|%s]] [[%s]]" % (name, ver,
                    strftime("%Y-%m-%d", gmtime(date)), name))
                out("[ [[%s|%d]] ] by [[%s]]\\\\" % (
                    url(self.request, "/+hg/rev/%d" % rev), rev, author))
                out(comment)
            text = "\n".join(lines)

        actions = [("/+feed/%s" % page_name or "", "RSS 1.0"),
                ("/+feed/%s?format=rss2" % page_name or "", "RSS 2.0"),
                ("/+feed/%s?format=atom" % page_name or "", "Atom")]

        return self._render("view.html", None,
                text=text, title=title, actions=actions)

    @expose("robots.txt")
    def robots(self, *args, **kwargs):
        node = short(self.storage.repo_node())
        self.response.headers.add_header("ETag", node)
        response = validate_etags(self.request, self.response)
        if response:
            return response

        self.response.headers["Content-Type"] = "text/plain"
        if "robots.txt" in self.storage:
            return self.storage.page_text("robots.txt")

        s = []
        s.append("User-agent: *")
        s.append("Disallow: /+*")
        s.append("Disallow: /%2b*")
        s.append("Disallow: /%2B*")
        return "\r\n".join(s)

def main():
    opts, args = parse_options()

    if opts.jit and psyco:
        psyco.full()

    if ":" in opts.bind:
        address, port = opts.bind.split(":")
        port = int(port)
    else:
        address, port = opts.bind, 8000

    bind = (address, port)

    manager = Manager()

    if opts.debug:
        manager += Debugger(events=False)

    poller = opts.poller.lower()
    if poller == "poll":
        Poller = Poll
    elif poller == "epoll":
        if EPoll is None:
            print "No epoll support available - defaulting to Select..."
            Poller = Select
        else:
            Poller = EPoll
    else:
        Poller = Select

    storage = WikiStorage(opts.data, opts.encoding)
    search = WikiSearch(opts.cache, storage)

    manager += (Poller()
            + Server(bind)
            + Gateway(hgweb(storage.repo_path), "/+hg")
            + Static(docroot="static")
            + Root(opts, storage, search)
            + Tools(opts, storage, search)
            + PluginManager(opts, storage, search)
            + Logger())

    if opts.daemon:
        manager += Daemon(opts.pidfile)

    manager.run()

if __name__ == "__main__":
    main()