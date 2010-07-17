"""HTML macros

Macros for generating snippets of HTML.
"""

from genshi.builder import tag
from genshi.filters import HTMLSanitizer

sanitizer = HTMLSanitizer()

from sahriswiki.highlight import highlight

def code(macro, environ, context, *args, **kwargs):
    """Render syntax highlighted code"""
    
    if not macro.body:
        return None

    lang = kwargs.get("lang", None)

    return highlight(macro.body, lang)

def source(macro, environ, context, *args, **kwargs):
    """Return the parsed text of body, rendered in a <pre> block."""
    
    if macro.body is None:
        return None

    return tag.pre(environ.parser.render(
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

    return tag.div(contents, id=id, class_=cls, style=style)

def span(macro, environ, context, cls=None, id=None, style=None,
        *args, **kwargs):
    """..."""

    if macro.body is None:
        return None

    if style:
        style = ';'.join(sanitizer.sanitize_css(style))

    contents = environ.parser.generate(
            macro.body, environ=environ, context='inline')
