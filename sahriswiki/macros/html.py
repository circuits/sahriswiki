# Module:   html
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""HTML Macros

Macros for generating snippets of HTML.
"""

from genshi.builder import tag
from genshi.filters import HTMLSanitizer

sanitizer = HTMLSanitizer()

from sahriswiki.highlight import highlight

def code(macro, environ, context, *args, **kwargs):
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

    return highlight(macro.body, lang=lang)

def div(macro, environ, context, *args, **kwargs):
    """Displays a block of text in a custom HTML <div>.
    
    This macro allows you to render a block of text in a custom HTML <div>
    block and contrib various attributes such as style, class, id, etc.

    **Arguments:**
    * id=None (//the id attribute//)
    * class=None (//the class attribute//)
    * float=None (//the float style//)
    * style=None (//the style attribute//)

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

    id = kwargs.get("id", None)
    cls = str(kwargs.get("class", None))
    float = kwargs.get("float", None)
    style = kwargs.get("style", None)

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

def span(macro, environ, context, *args, **kwargs):
    """Displays text in a HTML <span>

    This macro allows you to render a text in a custom HTML <span>
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

    text = macro.body or macro.arg_string

    if not text:
        return None

    id = kwargs.get("id", None)
    cls = str(kwargs.get("class", None))
    style = kwargs.get("style", None)

    if style:
        style = ";".join(sanitizer.sanitize_css(style))

    contents = environ.parser.generate(text, environ=(environ, context))

    return tag.span(contents, id=id, class_=cls, style=style)
