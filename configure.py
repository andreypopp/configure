"""

    configure -- configuration toolkit
    ==================================

    This module provides wrapper around PyYAML with the following features:

        * intepolation for string values

        * configuration merging

        * configuration inheritance (via 'extends' top-level attribute)

    Basic usage is:

        >>> from configure import Configuration
        >>> c = Configuration.from_file("./example.conf")
        >>> c.settings["a"]
        2

"""

import sys
from inspect import getargspec
from types import FunctionType
from re import compile as re_compile
from os import path
from collections import MutableMapping, Mapping
from datetime import timedelta
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

__all__ = (
    "Configuration", "ConfigurationError", "configure_logging",
    "format_config", "print_config")

class ConfigurationError(ValueError):
    """ Configuration error"""

class Configuration(MutableMapping):
    """ Configuration

    You should never instantiate this object but use ``from_file``,
    ``from_string`` or ``from_dict`` classmethods instead.

    Implements :class:`collections.MutableMapping` protocol.
    """

    def __init__(self, struct=None, ctx=None, parent=None):
        self.__struct = struct
        self.__ctx = ctx or {}
        self._parent = parent

    @property
    def _root(self):
        c = self
        while c._parent is not None:
            c = c._parent
        return c

    # Iterable
    def __iter__(self):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        return iter(self.__struct)

    # Container
    def __contains__(self, name):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        return name in self.__struct

    # Sized
    def __len__(self):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        return len(self.__struct)

    # Mapping
    def __getitem__(self, name):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        data = self.__struct[name]
        if isinstance(data, dict):
            return self.__class__(data, self.__ctx, parent=self)
        if isinstance(data, basestring):
            return data % self.__ctx
        return data

    # MutableMapping
    def __setitem__(self, name, value):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        self.__struct[name] = value

    # MutableMapping
    def __delitem__(self, name):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        self.__struct.__delitem__(name)

    def __getattr__(self, name):
        return self[name]

    def _merge(self, config):
        for k, v in config.items():
            if isinstance(v, Mapping) and k in self:
                if not isinstance(self[k], Mapping):
                    raise ConfigurationError(
                        "unresolveable conflict during merge")
                self[k]._merge(v)
            else:
                self[k] = v

    def merge(self, config):
        """ Merge configuration into this one"""
        new = self.__class__({}, parent=self._parent)
        new._merge(self)
        new._merge(config)
        return new

    def by_ref(self, path, value=None):
        if path[:2] == "..":
            path = path[1:]
            return self._parent.by_ref(path, value)

        if path[:1] != ".":
            return self._root.by_ref("." + path, value)

        path = path[1:]
        if "." in path:
            n, path = path.split(".", 1)
            n = self[n]
            if isinstance(n, Configuration):
                return n.by_ref("." + path, value)
            else:
                return obj_by_ref(n, path)
        else:
            if value is None:
                return self[path]
            else:
                self[path] = value
                return value

    def __add__(self, config):
        return self.merge(config)

    def configure(self, struct):
        """ Configure with other configuration object"""
        if isinstance(struct, self.__class__):
            struct = struct._Configuration__struct
        self.__struct = struct

    def configure_obj_graph(self):
        return configure_obj_graph(self)

    def __repr__(self):
        return repr(self.__struct)

    __str__ = __repr__

    @classmethod
    def from_file(cls, filename, ctx=None, constructors=None):
        """ Construct :class:`.Configuration` object by reading and parsing file
        ``filename``.

        :param filename:
            filename to parse config from
        :param ctx:
            mapping object used for value interpolation
        :param constructors:
            mapping of names to constructor for custom objects in YAML. Look at
            `_timedelta_constructor` and `_re_constructor` for examples.
        """
        with open(filename, "r") as f:
            cfg = cls(load(f.read(), constructors), ctx=ctx)
        if "extends" in cfg:
            supcfg_path = path.join(path.dirname(filename), cfg.pop("extends"))
            supcfg = cls.from_file(supcfg_path)
            cfg = supcfg + cfg
        return cfg

    @classmethod
    def from_string(cls, string, ctx=None, constructors=None):
        """ Construct :class:`.Configuration` from ``string``.

        :param string:
            string to parse config from
        :param ctx:
            mapping object used for value interpolation
        :param constructors:
            mapping of names to constructor for custom objects in YAML. Look at
            `_timedelta_constructor` and `_re_constructor` for examples.
        """
        return cls(load(string, constructors), ctx=ctx)

    @classmethod
    def from_dict(cls, d, ctx=None):
        """ Construct :class:`.Configuration` from dict ``d``.

        :param d:
            mapping object to use for config
        :param ctx:
            mapping object used for value interpolation
        """
        return cls(d, ctx=ctx)

def format_config(config, _lvl=0):
    indent = "  " * _lvl
    buf = ""
    for k, v in config.items():
        buf += "%s%s:\n" % (indent, k)
        if isinstance(v, Configuration):
            buf += format_config(v, _lvl + 1)
        else:
            buf += "%s%s\n" % ("  " * (_lvl + 1), v)
    return buf

def print_config(config):
    print format_config(config)

def configure_logging(logcfg=None, disable_existing_loggers=True):
    """ Configure logging in a sane way

    :param logcfg:
        may be a. a dict suitable for :func:`logging.config.dictConfig`, b.
        "syslog" string or c. None
    :param disable_existing_loggers:
        if we need to disable existing loggers
    """
    if logcfg is not None:
        if logcfg == "syslog":
            logcfg = {
                "handlers": {
                    "syslog": {
                        "class": "logging.handlers.SysLogHandler",
                        "formatter": "precise",
                    }
                },
                "root": {
                    "handlers": ["syslog"],
                    "level": "NOTSET",
                }
            }
    else:
        logcfg = {}

    if not "version" in logcfg:
        logcfg["version"] = 1

    if not "disable_existing_loggers" in logcfg:
        logcfg["disable_existing_loggers"] = disable_existing_loggers

    # formatters

    if not "formatters" in logcfg:
        logcfg["formatters"] = {}

    if not "brief" in logcfg["formatters"]:
        logcfg["formatters"]["brief"] = {
            "format": "%(message)s",
        }

    if not "precise" in logcfg["formatters"]:
        logcfg["formatters"]["precise"] = {
            "format": "%(asctime)s %(levelname)-8s %(name)-15s %(message)s",
        }

    # handlers

    if not "root" in logcfg:
        logcfg["root"] = {
            "handlers": ["console"],
            "level": "NOTSET",
        }

    if not "handlers" in logcfg:
        logcfg["handlers"] = {}

    if not "syslog" in logcfg["handlers"]:
        logcfg["handlers"]["syslog"] = {
            "class": "logging.handlers.SysLogHandler",
            "formatter": "precise",
            "level": "NOTSET",
        }

    if not "console" in logcfg["handlers"]:
        logcfg["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "formatter": "precise",
            "level": "NOTSET",
        }

    from logging.config import dictConfig
    dictConfig(logcfg)

def configure_obj(config, factory=None, ctx=None):
    config = dict(config)
    factory = config.pop("factory", None) or factory
    if not factory:
        raise ConfigurationError("cannot configure object without factory")
    if isinstance(factory, basestring):
        try:
            factory = import_string(factory)
        except ImportStringError as e:
            raise ConfigurationError("cannot import factory: %s" % e)
    if isinstance(factory, FunctionType):
        argspec = getargspec(factory)
    elif isinstance(factory, type):
        argspec = getargspec(factory.__init__)
        argspec = argspec._replace(args=argspec.args[1:])

    args = []
    kwargs = {}

    pos_cut = len(argspec.args) - len(argspec.defaults or [])

    for a in argspec.args[:pos_cut]:
        if not a in config:
            raise ConfigurationError(
                "missing '%s' argument for %s" % (a, factory))
        arg = config.pop(a)
        if isinstance(arg, (Ref, Obj)):
            arg = arg(ctx)
        args.append(arg)

    for a in argspec.args[pos_cut:]:
        if a in config:
            arg = config.pop(a)
            if isinstance(arg, (Ref, Obj)):
                arg = arg(ctx)
            kwargs[a] = arg

    if config:
        raise ConfigurationError(
            "extra arguments '%s' found for %s" % (config, factory))
    return factory(*args, **kwargs)

def configure_obj_graph(config):
    for k, v in config.iteritems():
        if isinstance(v, Obj):
            config[k] = v(config)
        if isinstance(v, Mapping):
            config[k] = configure_obj_graph(v)
    return config

def _timedelta_contructor(loader, node):
    item = loader.construct_scalar(node)

    if not isinstance(item, basestring) or not item:
        raise ConfigurationError(
            "value '%s' cannot be interpreted as date range" % item)
    num, typ = item[:-1], item[-1].lower()

    if not num.isdigit():
        raise ConfigurationError(
            "value '%s' cannot be interpreted as date range" % item)

    num = int(num)

    if typ == "d":
        return timedelta(days=num)
    elif typ == "h":
        return timedelta(seconds=num * 3600)
    elif typ == "w":
        return timedelta(days=num * 7)
    elif typ == "m":
        return timedelta(seconds=num * 60)
    else:
        raise ConfigurationError(
            "value '%s' cannot be interpreted as date range" % item)

def _re_constructor(loader, node):
    item = loader.construct_scalar(node)
    return re_compile(item)

class Ref(object):

    def __init__(self, ref):
        self.ref = ref

    def __call__(self, ctx):
        o = ctx.by_ref(self.ref)
        if isinstance(o, Obj):
            return ctx.by_ref(self.ref, o(ctx))
        return o

def _ref_constructor(loader, node):
    item = loader.construct_scalar(node)
    return Ref(item)

class Obj(object):

    def __init__(self, config):
        self.config = config

    def __call__(self, ctx):
        return configure_obj(self.config, ctx=ctx)

def _obj_constructor(loader, node):
    item = loader.construct_mapping(node)
    return Obj(item)

def load(stream, constructors=None):
    loader = Loader(stream)
    constructors = constructors or {}

    if not "timedelta" in constructors:
        loader.add_constructor("!timedelta", _timedelta_contructor)
    if not "re" in constructors:
        loader.add_constructor("!re", _re_constructor)
    if not "ref" in constructors:
        loader.add_constructor("!ref", _ref_constructor)
    if not "obj" in constructors:
        loader.add_constructor("!obj", _obj_constructor)

    if constructors:
        for name, constructor in constructors.items():
            loader.add_constructor("!" + name, constructor)

    try:
        return loader.get_single_data()
    finally:
        loader.dispose()

def import_string(import_name, silent=False):
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If `silent` is True the return value will be `None` if the import fails.

    For better debugging we recommend the new :func:`import_module`
    function to be used instead.

    :param import_name: the dotted name for the object to import.
    :param silent: if set to `True` import errors are ignored and
                   `None` is returned instead.
    :return: imported object

    :copyright: (c) 2011 by the Werkzeug Team
    """
    # force the import name to automatically convert to strings
    if isinstance(import_name, unicode):
        import_name = str(import_name)
    try:
        if ':' in import_name:
            module, obj = import_name.split(':', 1)
        elif '.' in import_name:
            module, obj = import_name.rsplit('.', 1)
        else:
            return __import__(import_name)
        # __import__ is not able to handle unicode strings in the fromlist
        # if the module is a package
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        try:
            return getattr(__import__(module, None, None, [obj]), obj)
        except (ImportError, AttributeError):
            # support importing modules not yet set up by the parent module
            # (or package for that matter)
            modname = module + '.' + obj
            __import__(modname)
            return sys.modules[modname]
    except ImportError, e:
        if not silent:
            raise ImportStringError(import_name, e), None, sys.exc_info()[2]

class ImportStringError(ImportError):
    """Provides information about a failed :func:`import_string` attempt.

    :copyright: (c) 2011 by the Werkzeug Team
    """

    #: String in dotted notation that failed to be imported.
    import_name = None
    #: Wrapped exception.
    exception = None

    def __init__(self, import_name, exception):
        self.import_name = import_name
        self.exception = exception

        msg = (
            'import_string() failed for %r. Possible reasons are:\n\n'
            '- missing __init__.py in a package;\n'
            '- package or module path not included in sys.path;\n'
            '- duplicated package or module name taking precedence in '
            'sys.path;\n'
            '- missing module, class, function or variable;\n\n'
            'Debugged import:\n\n%s\n\n'
            'Original exception:\n\n%s: %s')

        name = ''
        tracked = []
        for part in import_name.replace(':', '.').split('.'):
            name += (name and '.') + part
            imported = import_string(name, silent=True)
            if imported:
                tracked.append((name, imported.__file__))
            else:
                track = ['- %r found in %r.' % (n, i) for n, i in tracked]
                track.append('- %r not found.' % name)
                msg = msg % (import_name, '\n'.join(track),
                             exception.__class__.__name__, str(exception))
                break

        ImportError.__init__(self, msg)

    def __repr__(self):
        return '<%s(%r, %r)>' % (self.__class__.__name__, self.import_name,
                                 self.exception)

def obj_by_ref(o, path):
    for s in path.split("."):
        o = getattr(o, s)
    return o
