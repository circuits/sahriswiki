# Module:   html
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""HTML Macros

Macros for generating snippets of HTML.
"""

from genshi.input import HTML
from genshi.core import Markup
from genshi.builder import tag
from genshi.filters import HTMLSanitizer
from genshi.output import HTMLSerializer

sanitizer = HTMLSanitizer()
serializer = HTMLSerializer()

from sahriswiki.highlight import highlight

def code(macro, environ, data, *args, **kwargs):
    """Displays a block of text with syntax highlighting in a HTML <pre>.
    
    This macro uses the pygments syntax highlighter to render a block of
    text given a specific language. For a list of available languages
    that are supported by pygments see:
    * [[http://pygments.org/languages/]]

    If an invalid language is specified or a lexer cannot be found for the
    given language (//given by the lang argument//) then the block of text
    will be rendered unhighlighted.

    **Arguments:**
    * lang=None (//the language to highlight//)

    **Example(s):**
    {{{
    <<code lang="python">>
    def main():
        print "Hello World!"

    if __name__ == "__main__":
        main()
    <</code>>
    }}}

    <<code lang="python">>
    def main():
        print "Hello World!"

    if __name__ == "__main__":
        main()
    <</code>>
    """
    
    if not macro.body:
        return None

    lang = kwargs.get("lang", None)
    linenos = kwargs.get("linenos", False)

    return highlight(macro.body, lang=lang, linenos=linenos)

def div(macro, environ, data, *args, **kwargs):
    """Displays a block of text in a custom HTML <div>.
    
    This macro allows you to render a block of text in a custom HTML <div>
    block and contrib various attributes such as style, class, id, etc.

    **Arguments:**
    * id=None (//the id attribute//)
    * class=None (//the class attribute//)
    * float=None (//the float style//)
    * style=None (//the style attribute//)
    * context="block" (//Either "inline" or "block"//)

    **Example(s):**
    {{{
    <<div float="right">>
    Hello World!
    <</div>>
    }}}

    <<div float="right">>
    Hello World!
    <</div>>
    """

    if macro.body is None:
        return None

    id = kwargs.get("id", "")
    cls = kwargs.get("class", "")
    float = kwargs.get("float", "")
    style = kwargs.get("style", "")
    parse = kwargs.get("parse", True)
    context = kwargs.get("context", "block")

    if float and float in ("left", "right"):
        style = "float: %s; %s" % (float, style)

    if style:
        style = ";".join(sanitizer.sanitize_css(style))

    contents = environ.parser.generate(macro.body, context=context,
            environ=(environ, data))

    attrs = {}
    if id:
        attrs["id"] = id
    if cls:
        attrs["class_"] = cls
    if style:
        attrs["style"] = style

    return tag.div(contents, **attrs)

def span(macro, environ, data, *args, **kwargs):
    """Displays text in a HTML <span>

    This macro allows you to display text in a custom HTML <span>
    element and contrib various attributes such as style, class, id, etc.
    
    **Arguments:**
    * id=None (//the id attribute//)
    * class=None (//the class attribute//)
    * style=None (//the style attribute//)

    **Example(s):**
    {{{
    <<span "Hello World!">>
    }}}

    <<span "Hello World!">>
    """

    text = macro.body or (args and args[0]) or None

    if not text:
        return None

    id = kwargs.get("id", None)
    cls = str(kwargs.get("class", None))
    style = kwargs.get("style", None)

    if style:
        style = ";".join(sanitizer.sanitize_css(style))

    contents = environ.parser.generate(text, context="inline",
            environ=(environ, data))

    attrs = {}
    if id:
        attrs["id"] = id
    if cls:
        attrs["class_"] = cls
    if style:
        attrs["style"] = style

    return tag.span(contents, **attrs)

def p(macro, environ, data, *args, **kwargs):
    """Displays text in a HTML <p>

    This macro allows you to display text in a custom HTML <p>
    element and contrib various attributes such as style, class, id, etc.
    
    **Arguments:**
    * id=None (//the id attribute//)
    * class=None (//the class attribute//)
    * style=None (//the style attribute//)

    **Example(s):**
    {{{
    <<p "Hello World!">>
    }}}

    <<p "Hello World!">>
    """

    text = macro.body or (args and args[0]) or None

    if not text:
        return None

    id = kwargs.get("id", None)
    cls = str(kwargs.get("class", None))
    style = kwargs.get("style", None)

    if style:
        style = ";".join(sanitizer.sanitize_css(style))

    contents = environ.parser.generate(text, context="inline",
            environ=(environ, data))

    attrs = {}
    if id:
        attrs["id"] = id
    if cls:
        attrs["class_"] = cls
    if style:
        attrs["style"] = style

    return tag.p(contents, **attrs)

def html(macro, environ, data, *args, **kwargs):
    """Displays raw HTML content.

    This macro allows you to display raw HTML with any **safe** content.

    **NB:** Any elements considered unsafe are automatically stripped.
    
    **Arguments:** //No Arguments//

    **Example(s):**
    {{{
    <<html>>
    <h1>Hello World!</h1>
    <</html>>
    }}}

    <<html>>
    <h1>Hello World!</h1>
    <</html>>
    """

    if not macro.body:
        return None

    return Markup("".join(serializer(sanitizer(HTML(macro.body)))))

def img(macro, environ, data, *args, **kwargs):
    """Displays an image, HTML <img>.

    This macro allows you to display a custom image, HTML <img>
    element and contrib various attributes such as style, class, id, etc.
    
    **Arguments:**
    * id=None (//the id attribute//)
    * alt=None (//the alt attribute//)
    * class=None (//the class attribute//)
    * style=None (//the style attribute//)

    **Example(s):**
    {{{
    <<img "/img/python.png">>
    }}}

    <<img "/img/python.png">>
    """

    if not args:
        return None

    src = args[0]

    id = kwargs.get("id", None)
    alt = kwargs.get("alt", None)
    cls = kwargs.get("class", None)
    style = kwargs.get("style", None)

    if style:
        style = ";".join(sanitizer.sanitize_css(style))

    attrs = {}
    if id:
        attrs["id"] = id
    if alt:
        attrs["alt"] = alt
    if cls:
        attrs["class_"] = cls
    if style:
        attrs["style"] = style

    return tag.img(src=src, **attrs)
