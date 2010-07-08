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
