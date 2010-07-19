# -*- coding: utf-8 -*-
# Module:   utils
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Utility Functions

...
"""

import re

from circuits.web.tools import mimetypes

NEWLINES = re.compile("\n|\r[^\n]|\r\n")

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

def page_mime(title, types=[("+", "type")], default="text/x-wiki"):
    """
    Guess page's mime type ased on corresponding file name.

    Files that start with a type prefix (the first item of each item
    in the type list) then the type if returned for that file (the
    second item of th matching item in the type list).

    If nothing else matches, default is returned.

    >>> page_mime(u'something.txt')
    'text/plain'
    >>> page_mime(u'SomePage')
    'text/x-wiki'
    >>> page_mime(u'ąęśUnicodePage')
    'text/x-wiki'
    >>> page_mime(u'image.png')
    'image/png'
    >>> page_mime(u'style.css')
    'text/css'
    >>> page_mime(u'archive.tar.gz')
    'archive/gzip'
    >>> page_mime(u'+history')
    'type/history'
    """

    addr = title.encode('utf-8') # the encoding doesn't relly matter here
    mime, encoding = mimetypes.guess_type(addr, strict=False)

    if encoding:
        return 'archive/%s' % encoding

    if mime is None:
        for prefix, type in types:
            if title.startswith(prefix):
                return "/".join([type, title[title.find(prefix) + 1:]])
        return default
    return mime

def extract_links(text):
    links = re.compile(ur"\[\[(?P<link_target>([^|\]]|\][^|\]])+)"
            ur"(\|(?P<link_text>([^\]]|\][^\]])+))?\]\]")

    for m in links.finditer(text):
        if m.groupdict():
            d = m.groupdict()
            yield d["link_target"], d["link_text"] or ""
