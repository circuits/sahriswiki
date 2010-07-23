# Module:   utils
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Utility Macros

Various Utility Macros
"""

from inspect import getdoc

def macros(macro, environ, data, *args, **kwargs):
    """Display a list of available macros and their documentation.
    
    **Arguments:** //No Arguments//

    **Example(s):**
    {{{
    <<macros>>
    }}}

    You're looking at it! :)
    """

    macros = environ.macros.items()
    s = "\n".join(["== %s ==\n%s\n" % (k, getdoc(v)) for k, v in macros])

    return environ.parser.generate(s, context="inline",
            environ=(environ, data))
