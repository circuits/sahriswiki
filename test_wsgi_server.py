#!/usr/bin/env python


from __future__ import print_function

from wsgiref.simple_server import make_server


from sahriswiki.wsgi import application


httpd = make_server("", 8000, application)
print("Serving on port 8000...")
httpd.serve_forever()
