"""Include macros

Macros for inclusion of other wiki pages
"""

from genshi import builder

def include(macro, environ, name=None, *args, **kwargs):
    """Return the parsed content of the page identified by arg_string"""
    
    if name is None:
        return None

    storage = environ.storage

    if name in storage:
        text = storage.page_text(name)

        environ.page["name"] = name
        environ.page["text"] = text

        return environ.parser.generate(text, environ=environ)

def include_raw(macro, environ, name=None, *args, **kwargs):
    """Return the raw text of the page identified by arg_string, rendered
    in a <pre> block.
    """

    if name is None:
        return None

    storage = environ.storage

    if name in storage:
        text = storage.page_text(name)

        return builder.tag.pre(text, class_="plain")

def include_source(macro, environ, name=None, *args, **kwargs):
    """Return the parsed text of the page identified by arg_string, rendered
    in a <pre> block.
    """

    if name is None:
        return None

    storage = environ.storage

    if name in storage:
        text = storage.page_text(name)

        environ.page["name"] = name

        return builder.tag.pre(environ.parser.render(text,
            environ=environ).decode("utf-8"))
