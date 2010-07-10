# -*- coding: utf-8 -*-

from circuits.web.tools import mimetypes

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

def page_mime(title):
    """
    Guess page's mime type ased on corresponding file name.
    Default ot text/x-wiki for files without an extension.

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
    """

    addr = title.encode('utf-8') # the encoding doesn't relly matter here
    mime, encoding = mimetypes.guess_type(addr, strict=False)
    if encoding:
        mime = 'archive/%s' % encoding
    if mime is None:
        mime = 'text/x-wiki'
    return mime
