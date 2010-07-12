# Module:   dbapi
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""DB-API Wrapper Classes

...
"""

import re
from itertools import izip as zip

from pyodict import odict

ORACLE_ARRAYSIZE = 2048

def create_connection(s, **kwargs):
    d = parse_uri(s)
    schema = d["schema"]
    username = d["username"]
    password = d["password"]
    hostname = d["hostname"]
    database = d["database"]

    if schema.lower() == "oracle":
        try:
            import cx_Oracle as oracle
        except:
            raise DriverError("oracle", "No Oracle support available.")

        try:
            return OracleSession(oracle.connect(
                dsn=hostname, user=username,
                password=password), **kwargs)
        except Exception, e:
            raise ConnectionError("oracle", e)

    elif schema.lower() == "mysql":
        try:
            import MySQLdb as mysql
        except:
            raise DriverError("mysql", "No MySQL support available.")

        try:
            return MySQLSession(mysql.connect(
                host=hostname,  user=username,
                passwd=password, db=database), **kwargs)
        except Exception, e:
            raise ConnectionError("mysql", e)

    elif schema.lower() == "sqlite":
        try:
            import sqlite3 as sqlite
        except:
            raise DriverError("sqlite", "No SQLite support available.")

        if database.lower() == ":memory:":
            filename = ":memory:"
        else:
            import os
            filename = os.path.abspath(
                    os.path.expanduser(database))

        try:
            return SQLiteSession(
                    sqlite.connect(filename), **kwargs)
        except sqlite.Error, e:
            raise ConnectionError("sqlite", e)

def parse_uri(s):
    m = re.match("(?P<schema>oracle|mysql|sqlite)://"
            "((?P<username>.*?):(?P<password>.*?)@(?P<hostname>.*?)/)?"
            "(?P<database>.*)",
            s, re.IGNORECASE)
    return m.groupdict()

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

    def close(self):
        self._cx.close()

    def rollback(self):
        elf._cx.rollback()

    def _execute(self, sql=None, *args, **kwargs):
        pass

    def commit(self):
        self._cx.commit()

    def cursor(self, create=False):
        if create:
            return self._cx.cursor()
        else:
            return self._cu

    def execute(self, sql=None, *args, **kwargs):
        try:
            self._execute(sql, *args, **kwargs)
            return Records(self, self.getCursor())
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

    def __init__(self, *args, **kwargs):
        super(OracleSession, self).__init__(*args, **kwargs)

        self.getCursor().arraysize = ORACLE_ARRAYSIZE

    def _execute(self, sql=None, *args, **kwargs):
        self._cu.execute(sql, *args, **kwargs)

Connection = create_connection

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

        for k, v in data:
            self.add(k, v)
    
    def add(self, k, v):
        if type(k) == tuple:
            k = k[0]

        if isinstance(v, self.records.cursor.__class__):
            if self.records.cursor.description is not None:
                fields = map(lambda x: x[0], v.description)
                v = Records(self.records, v)

        self[k] = v
        setattr(self, k, v)

    def remove(self, k):
        del self[k]
        delattr(self, k)
