"""

    configure.module -- module synthesize utility
    =============================================

"""

from types import ModuleType
from zope.proxy import ProxyBase, setProxiedObject
from configure import ConfigurationError

__all__ = ('ConfigurationModule', 'bootstrap')

class ConfigurationModule(ModuleType):

    def __init__(self, name):
        super(ConfigurationModule, self).__init__(name)
        self.proxies = {}

    def configure(self, config):
        for k, v in self.proxies.items():
            if k in ("__path__",):
                continue
            if not k in config:
                raise ConfigurationError()
            setProxiedObject(v, config[k])
            self.proxies.pop(k)
        if self.proxies:
            raise ConfigurationError()

    def __getattr__(self, name):
        if name in ("__path__",):
            return ModuleType.__getattr__(self, name)
        if name in self.proxies:
            return self.proxies[name]
        proxy = ProxyBase(None)
        self.proxies[name] = proxy
        return proxy

    @classmethod
    def bootstrap(cls):
        """ Mark module as configuration module"""
        import sys
        fr = sys._getframe()
        fr = fr.f_back
        if not "__name__" in fr.f_globals:
            raise ValueError("this function should be called at module level")
        mod = fr.f_globals["__name__"]
        sys.modules[mod] = cls(mod)

bootstrap = ConfigurationModule.bootstrap
