# Module:   auth
# Date:     25th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Authentication / Permissions

...
"""

import schema

class Permissions(object):

    def __init__(self, environ, username):
        super(Permissions, self).__init__()

        self.environ = environ
        self.username = username

        self._actions = []

        db = self.environ.dbm.session
        self._actions = [permission.action \
                for permission in db.query(schema.Permission).\
                filter(schema.Permission.username==self.username)]

    def __contains__(self, action):
        return action in self._actions or "SAHRIS_ADMIN" in self._actions

    def __repr__(self):
        return "<Permissions(%s %r)>" % (self.username, self._actions)
