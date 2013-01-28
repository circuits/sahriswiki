#!/usr/bin/env python

from .helpers import urlencode, urlopen, HTTPError


def test_init(webapp):
    f = urlopen(webapp.server.base)
    s = f.read()
    assert s == b"Hello World!"
