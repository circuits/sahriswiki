"""Wiki macros"""

from genshi import builder

def title(macro, environ, *args, **kwargs):
    """Return the title of the current page."""

    return environ["page"]["name"]
