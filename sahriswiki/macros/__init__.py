# Module:   macros
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Macro Support

Macro loader and dispatcher for creoleparser
"""

import os
from traceback import format_exc
from inspect import getmembers, getmodule, isfunction

from genshi.builder import tag

from sahriswiki.unrepr import unrepr
from sahriswiki.highlight import highlight
from sahriswiki.creoleparser.core import ArgParser
from sahriswiki.creoleparser.dialects import ArgDialect
from sahriswiki.creoleparser.elements import KeywordArg, WhiteSpace

def creepy10_base():

    class Base(ArgDialect):

        kw_arg = KeywordArg(token='=')
        spaces = WhiteSpace()

        def __init__(self):
            self.kw_arg.child_elements = [self.spaces]

        @property
        def top_elements(self):
            return [self.kw_arg]

    return Base

def arg_func(arg):
    try:
        return unrepr(arg)
    except:
        return arg

def key_func(k, v):
    try:
        return k, unrepr(v)
    except:
        return k, v

parse_args = ArgParser(
    dialect=creepy10_base(),
    arg_func=arg_func,
    key_func=key_func,
)

class Macro(object):

    def __init__(self, name, arg_string, body, isblock):
        super(Macro, self).__init__()

        self.name = name
        self.arg_string = arg_string
        self.body = body
        self.isblock = isblock

def dispatcher(name, arg_string, body, isblock, (environ, data)):
    if name in environ.macros:
        macro = Macro(name, arg_string, body, isblock)
        args, kwargs = parse_args(arg_string)
        try:
            return environ.macros[name](macro, environ, data,
                *args, **kwargs)
        except Exception, e:
            error = "ERROR: Error while executing macro %s (%s)" % (name, e)
            traceback = format_exc()
            return tag.div(
                tag.p(error),
                highlight(traceback, lang="pytb"),
                class_="error"
            )

    else:
        return tag.div(tag.p("Macro %s Not Found!" % name), class_="error")

def loadMacros():
    path = os.path.abspath(os.path.dirname(__file__))
    p = lambda x: os.path.splitext(x)[1] == ".py"
    modules = [x for x in os.listdir(path) if p(x) and not x == "__init__.py"]

    macros = {}

    for module in modules:
        name, _ = os.path.splitext(module)

        moduleName = "%s.%s" % (__package__, name)
        m = __import__(moduleName, globals(), locals(), __package__)

        p = lambda x: isfunction(x) and getmodule(x) is m
        for name, function in getmembers(m, p):
            name = name.replace("_", "-")
            try:
                macros[name] = function
            except Exception, e:
                continue

    return macros
