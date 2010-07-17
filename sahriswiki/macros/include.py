"""Include macros

Macros for inclusion of other wiki pages
"""

from genshi import builder

from sahriswiki.errors import NotFoundErr

def include(macro, environ, context, name=None, *args, **kwargs):
    """Return the parsed content of the page identified by arg_string"""
    
    if name is None:
        return None

    return environ.include(name)

def include_raw(macro, environ, context, name=None, *args, **kwargs):
    """Return the raw text of the page identified by arg_string, rendered
    in a <pre> block.
    """

    if name is None:
        return None

    storage = environ.storage

    if name in storage:
        try:
            text = storage.page_text(name)
        except NotFoundErr:
            text = u""

        return builder.tag.pre(text, class_="plain")

def include_source(macro, environ, context, name=None, *args, **kwargs):
    """Return the parsed text of the page identified by arg_string, rendered
    in a <pre> block.
    """

    if name is None:
        return None

    storage = environ.storage

    if name in storage:
        try:
            text = storage.page_text(name)
        except NotFoundErr:
            text = u""

        return builder.tag.pre(
            environ.parser.generate(text, environ=(environ, context))
        )
