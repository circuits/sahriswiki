# Module:   include
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Include macro

Macro for inclusion of other wiki pages
"""

from genshi.builder import tag
from genshi.output import HTMLSerializer

serializer = HTMLSerializer()

def include(macro, environ, data, *args, **kwargs):
    """Include the contents of another wiki page.
    
    This macro allows you to include the contents of another wiki page,
    optinoally allowing you to include it parsed (//the default//) or
    unparsed (//parse=False//). If the specified page does not exist,
    then "Page Not Found" will be displayed.

    **Arguments:**
    * name=None (//the name of the page to include//)
    * parse=True (//whether to parse the page//)
    * source=False (//whether to display the genereated HTML / source//)

    **Example(s):**
    {{{
    <<include "SandBox">>
    }}}

    <<include "SandBox">>

    {{{
    <<include "SandBox", parse=False>>
    }}}

    <<include "SandBox", parse=False>>
    """
    
    name = kwargs.get("name", (args and args[0]) or None)

    if name is None:
        return None

    parse = kwargs.get("parse", True)
    source = kwargs.get("source", False)

    contents = environ.include(name, parse, data=data)

    if source:
        return tag.pre("".join(serializer(contents)))
    else:
        return contents
