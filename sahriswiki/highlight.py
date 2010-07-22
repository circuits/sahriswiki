# Module:   highlight
# Date:     17th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Highlighting

...
"""

import pygments
import pygments.util
import pygments.lexers
import pygments.formatters

from genshi import Markup
from genshi.builder import tag

class HTMLFormatter(pygments.formatters.HtmlFormatter):

    def wrap(self, source, outfile):
        return self._wrap_code(source)

    def _wrap_code(self, source):
        yield 0, "<pre xml:space=\"preserve\">"
        for i, t in source:
            if not t.strip():
                t = "<br />"
            yield i, t
        yield 0, "</pre>"

def highlight(text, mime=None, lang=None, linenos=False):
    formatter = HTMLFormatter(cssclass="code", linenos=linenos)

    try:
        if mime:
            lexer = pygments.lexers.get_lexer_for_mimetype(mime)
        elif lang:
            lexer = pygments.lexers.get_lexer_by_name(lang)
        else:
            lexer = pygments.lexers.guess_lexer(text)
    except pygments.util.ClassNotFound:
        return tag.pre(text)

    return Markup(pygments.highlight(text, lexer, formatter))
