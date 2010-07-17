"""HTML macros

Macros for generating snippets of HTML.
"""

import genshi
import pygments
import pygments.util
import pygments.lexers
import pygments.formatters
from genshi import builder
from genshi.filters import HTMLSanitizer

sanitizer = HTMLSanitizer()

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

def code(macro, environ, context, *args, **kwargs):
    """Render syntax highlighted code"""
    
    if not macro.body:
        return None

    lang = kwargs.get("lang", None)

    if lang is not None:
        if not macro.isblock:
            return None
        try:
            lexer = pygments.lexers.get_lexer_by_name(lang, stripall=True)
        except pygments.util.ClassNotFound:
            return None
    else:
        lexer = None

    attrs = {
        "xml:space": "preserve",
    }

    if lexer:
        text = pygments.highlight(macro.body, lexer, HTMLFormatter())
        output = genshi.core.Markup(text)
    elif macro.isblock:
        output = genshi.builder.tag.pre(macro.body, attrs)
    else:
        output = genshi.builder.tag.code(macro.body, attrs)

    return output

def source(macro, environ, context, *args, **kwargs):
    """Return the parsed text of body, rendered in a <pre> block."""
    
    if macro.body is None:
        return None

    return builder.tag.pre(environ.parser.render(
        macro.body, environ=environ).decode("utf-8"))

def div(macro, environ, context, cls=None, float=None, id=None, style=None,
        *args, **kwargs):

    if macro.body is None:
        return None

    if float and float in ("left", "right"):
        style = "float: %s; %s" % (float, style)

    if style:
        style = ";".join(sanitizer.sanitize_css(style))

    if macro.isblock:
        context = "block"
    else:
        context = "inline"

    contents = environ.parser.generate(
            macro.body, environ=(environ, context))

    return builder.tag.div(contents, id=id, class_=cls, style=style)

def span(macro, environ, context, cls=None, id=None, style=None,
        *args, **kwargs):
    """..."""

    if macro.body is None:
        return None

    if style:
        style = ';'.join(sanitizer.sanitize_css(style))

    contents = environ.parser.generate(
            macro.body, environ=environ, context='inline')
