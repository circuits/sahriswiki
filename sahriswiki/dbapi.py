# Module:   dbapi
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""DB-API Wrapper Classes

...
"""

from itertools import izip as zip

from pyodict import odict

def mysql_session(*args, **kwargs):
    try:
        from MySQLdb import Connection
    except:
        raise DriverError("mysql", "No MySQL support available.")

    try:
        return MySQLSession(Connection(*args, **kwargs))
    except Exception, e:
        raise ConnectionError("mysql", e)

def oracle_session(*args, **kwargs):
    try:
        from cx_Oracle import Connection
    except:
        raise DriverError("oracle", "No Oracle support available.")

    try:
        return OracleSession(Connection(*args, **kwargs))
    except Exception, e:
        raise ConnectionError("oracle", e)

def sqlite_session(*args, **kwargs):
    try:
        from sqlite3 import Connection
    except:
        raise DriverError("sqlite", "No SQLite support available.")

    try:
        return SQLiteSession(Connection(*args, **kwargs))
    except sqlite.Error, e:
        raise ConnectionError("sqlite", e)

types = {
    "mysql": mysql_session,
    "oracle": oracle_session,
    "sqlite": sqlite_session,
}

def create_connection(type, *args, **kwargs):
    return types[type](*args, **kwargs)

Connection = create_connection

class DriverError(Exception):

    def __init__(self, driver, msg):
        super(DriverError, self).__init__(msg)

        self.driver = driver

class ConnectionError(Exception):

    def __init__(self, driver, e):
        super(ConnectionError, self).__init__(e)

        self.driver = driver

class DatabaseError(Exception):

    def __init__(self, sql, e):
        super(DatabaseError, self).__init__(e)

        self.sql = sql

class BaseSession(object):

    def __init__(self, cx):
        "initializes x; see x.__class__.__doc__ for signature"

        self._cx = cx
        self._cu = self.cursor(True)

    def _execute(self, sql=None, *args, **kwargs):
        pass

    def cursor(self, create=False):
        if create:
            return self._cx.cursor()
        else:
            return self._cu

    def close(self):
        self._cx.close()

    def rollback(self):
        self._cx.rollback()

    def commit(self):
        self._cx.commit()

    def execute(self, sql=None, *args, **kwargs):
        try:
            if args:
                self._execute(sql, *args)
            elif kwargs:
                self._execute(sql, **kwargs)
            else:
                self._execute(sql)
            return Records(self, self.cursor())
        except Exception, e:
            raise DatabaseError(sql, e)

    do = execute

class SQLiteSession(BaseSession):

    def _execute(self, sql=None, *args, **kwargs):
        self._cu.execute(sql, args)

class MySQLSession(BaseSession):

    def _execute(self, sql=None, *args, **kwargs):
        self._cu.execute(sql, args)

class OracleSession(BaseSession):

    ORACLE_ARRAYSIZE = 2048

    def __init__(self, *args, **kwargs):
        super(OracleSession, self).__init__(*args, **kwargs)

        self.getCursor.arraysize = ORACLE_ARRAYSIZE

    def _execute(self, sql=None, *args, **kwargs):
        self._cu.execute(sql, *args, **kwargs)

class Records(object):

    def __init__(self, session, cursor):
        "initializes x; see x.__class__.__doc__ for signature"

        super(Records, self).__init__()

        self.session = session
        self.cursor = cursor

        if self.cursor.description is not None:
            self.fields = [x[0] for x in self.cursor.description]
        else:
            self.fields = []

    def __repr__(self):
        return "<%s %d rows>" % (self.__class__.__name__, len(self))
        
    def __iter__(self):
        "x.__iter__() <==> iter(x)"

        return self

    def __len__(self):
        "x.__len__() <==> len(x)"

        return self.cursor.rowcount

    def next(self):
        "x.next() -> the next value, or raise StopIteration"

        row = self.cursor.fetchone()
        if row:
            return Record(self, zip(self.fields, row))
        else:
            raise StopIteration

class Record(odict):

    def __init__(self, records, data):
        "initializes x; see x.__class__.__doc__ for signature"

        super(Record, self).__init__()

        self.records = records

        self.update(data)

    def __repr__(self):
        return "<%s (%r)>" % (self.__class__.__name__, self.keys())

    def __setitem__(self, k, v):
        if type(k) == tuple:
            k = k[0]

        if isinstance(v, self.records.cursor.__class__):
            if self.records.cursor.description is not None:
                fields = map(lambda x: x[0], v.description)
                v = Records(self.records, v)

        super(Record, self).__setitem__(k, v)
        setattr(self, k, v)

    def __delitem__(self, k):
        super(Record, self).__delitem__(k)
        delattr(self, k)
