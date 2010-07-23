# Module:   dbm
# Date:     24th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""DataBase Manager

...
"""

from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, MetaData, String

from circuits import handler, BaseComponent

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class SysInfo(Base):

    __tablename__ = "sysinfo"

    name = Column(String(20), primary_key=True)
    value = Column(String(80))

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return "<SysInfo('%s', '%s')>" % (self.name, self.value)

class DataBaseManager(BaseComponent):

    def __init__(self, dburi, echo=False, convert_unicode=True):
        super(DataBaseManager, self).__init__()

        self.metadata = metadata

        self.engine = create_engine(dburi,
            echo=echo,
            convert_unicode=convert_unicode,
        )

        self.session = scoped_session(
            sessionmaker(
                bind=self.engine,
                autoflush=True,
                autocommit=False,
            )
        )

    @handler("started", priority=1.0, target="*")
    def _on_started(self, component, mode):
        self.metadata.create_all(self.engine)

    @handler("stopped", target="*")
    def _on_stopped(self, component):
        self.session.flush()
        self.session.commit()
        self.session.close()
