# Module:   reprconf
# Date:     15th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au
# NOTE:     Borrowed from CherryPy3

"""Generic configuration system using unrepr.

Configuration data may be supplied as a Python dictionary, as a filename,
or as an open file object. When you supply a filename or file, Python's
builtin ConfigParser is used (with some extensions).
"""

import sys
import operator as _operator
from ConfigParser import ConfigParser

def as_dict(config):
    """Return a dict from 'config' whether it is a dict, file, or filename."""
    if isinstance(config, str):
        config = Parser().dict_from_file(config)
    elif hasattr(config, 'read'):
        config = Parser().dict_from_file(config)
    return config

class Config(dict):
    """A dict-like set of configuration data.
    
    May take a file, filename, or dict.
    """
    
    defaults = {}
    environments = {}
    
    def __init__(self, file=None, **kwargs):
        super(Config, self).__init__()

        self.reset()
        if file is not None:
            self.update(file)
        if kwargs:
            self.update(kwargs)
    
    def reset(self):
        """Reset self to default values."""
        self.clear()
        dict.update(self, self.defaults)
    
    def update(self, config):
        """Update self from a dict, file or filename."""
        if isinstance(config, str):
            # Filename
            config = Parser().dict_from_file(config)
        elif hasattr(config, 'read'):
            # Open file object
            config = Parser().dict_from_file(config)
        else:
            config = config.copy()
        self._apply(config)
    
    def _apply(self, config):
        """Update self from a dict."""
        which_env = config.get('environment')
        if which_env:
            env = self.environments[which_env]
            for k in env:
                if k not in config:
                    config[k] = env[k]
        
        dict.update(self, config)

    def __setitem__(self, k, v):
        dict.__setitem__(self, k, v)

class Parser(ConfigParser):
    """Sub-class of ConfigParser that keeps the case of options and that raises
    an exception if the file cannot be read.
    """
    
    def optionxform(self, optionstr):
        return optionstr
    
    def read(self, filenames):
        if isinstance(filenames, str):
            filenames = [filenames]
        for filename in filenames:
            # try:
            #     fp = open(filename)
            # except IOError:
            #     continue
            fp = open(filename)
            try:
                self._read(fp, filename)
            finally:
                fp.close()
    
    def as_dict(self, raw=False, vars=None):
        """Convert an INI file to a dictionary"""
        # Load INI file into a dict
        result = {}
        for section in self.sections():
            if section not in result:
                result[section] = {}
            for option in self.options(section):
                value = self.get(section, option, raw, vars)
                try:
                    value = unrepr(value)
                except Exception as x:
                    msg = ("Config error in section: %r, option: %r, "
                           "value: %r. Config values must be valid Python." %
                           (section, option, value))
                    raise ValueError(msg, x.__class__.__name__, x.args)
                result[section][option] = value
        return result
    
    def dict_from_file(self, file):
        if hasattr(file, 'read'):
            self.readfp(file)
        else:
            self.read(file)
        return self.as_dict()


# public domain "unrepr" implementation, found on the web and then improved.

class _Builder:
    
    def build(self, o):
        m = getattr(self, 'build_' + o.__class__.__name__, None)
        if m is None:
            raise TypeError("unrepr does not recognize %s" %
                            repr(o.__class__.__name__))
        return m(o)
    
    def build_Subscript(self, o):
        return self.build(o.value)[self.build(o.slice)]
    
    def build_Index(self, o):
        return self.build(o.value)
    
    def build_Call(self, o):
        callee = self.build(o.func)
        
        if o.args is None:
            args = ()
        else: 
            args = tuple([self.build(a) for a in o.args]) 
        
        if o.starargs is None:
            starargs = ()
        else:
            starargs = self.build(o.starargs)
        
        if o.kwargs is None:
            kwargs = {}
        else:
            kwargs = self.build(o.kwargs)
        
        return callee(*(args + starargs), **kwargs)
    
    def build_List(self, o):
        return list(map(self.build, o.elts))
    
    def build_Str(self, o):
        return o.s
    
    def build_Num(self, o):
        return o.n
    
    def build_Dict(self, o):
        return dict([(self.build(k), self.build(v))
                     for k, v in zip(o.keys, o.values)])
    
    def build_Tuple(self, o):
        return tuple(self.build_List(o))
    
    def build_Name(self, o):
        name = o.id
        if name == 'None':
            return None
        if name == 'True':
            return True
        if name == 'False':
            return False
        
        # See if the Name is a package or module. If it is, import it.
        try:
            return modules(name)
        except ImportError:
            pass
        
        # See if the Name is in builtins.
        try:
            import builtins
            return getattr(builtins, name)
        except AttributeError:
            pass
        
        raise TypeError("unrepr could not resolve the name %s" % repr(name))
    
    def build_BinOp(self, o):
        left, op, right = map(self.build, [o.left, o.op, o.right]) 
        return op(left, right)

    def build_Add(self, o):
        return _operator.add

    def build_Attribute(self, o):
        parent = self.build(o.value)
        return getattr(parent, o.attr)

    def build_NoneType(self, o):
        return None


def _astnode(s):
    """Return a Python ast Node compiled from a string."""
    try:
        import ast
    except ImportError:
        # Fallback to eval when ast package is not available,
        # e.g. IronPython 1.0.
        return eval(s)

    p = ast.parse("__tempvalue__ = " + s)
    return p.body[0].value

def unrepr(s):
    """Return a Python object compiled from a string."""
    if not s:
        return s
    obj = _astnode(s)
    return _Builder().build(obj)


def modules(modulePath):
    """Load a module and retrieve a reference to that module."""
    try:
        mod = sys.modules[modulePath]
        if mod is None:
            raise KeyError()
    except KeyError:
        # The last [''] is important.
        mod = __import__(modulePath, globals(), locals(), [''])
    return mod

def attributes(full_attribute_name):
    """Load a module and retrieve an attribute of that module."""
    
    # Parse out the path, module, and attribute
    last_dot = full_attribute_name.rfind(".")
    attr_name = full_attribute_name[last_dot + 1:]
    mod_path = full_attribute_name[:last_dot]
    
    mod = modules(mod_path)
    # Let an AttributeError propagate outward.
    try:
        attr = getattr(mod, attr_name)
    except AttributeError:
        raise AttributeError("'%s' object has no attribute '%s'"
                             % (mod_path, attr_name))
    
    # Return a reference to the attribute.
    return attr


