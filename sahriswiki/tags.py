# Module:   tags
# Date:     24th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Tags and Tagging SUpport

...
"""

from sqlalchemy import Column, Index, String

from dbm import Base

class Tags(Base):

    __tablename__ = "tags"

    tagspace = Column(String(50), primary_key=True)
    name = Column(String(50), primary_key=True)
    tag = Column(String(50), primary_key=True)

    def __init__(self, tagspace, name, tag):
        self.tagspace = tagspace
        self.name = name
        self.tag = tag

    def __repr__(self):
        return "<Tag('%s', '%s', '%s')>" % (self.tagspace, self.name, self.tag)

Index("idx_name", Tags.tagspace, Tags.name)
Index("idx_tag", Tags.tagspace, Tags.tag)
