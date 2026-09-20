from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlparse
from .application_connectors import ApplicationConnector, GuidedBrowserConnector, AuthorizedApiConnector

@dataclass(frozen=True)
class AdapterCapability:
    name: str
    mode: str
    requires_user_submit: bool
    supports_recovery: bool

class SourceApplicationAdapter(ApplicationConnector):
    source_key='generic'
    capability=AdapterCapability('generic_browser','GUIDED_BROWSER',True,True)
    def __init__(self, source_key=None):
        self.source_key=source_key or self.source_key
    def plan(self, opportunity, profile, proposal):
        return GuidedBrowserConnector().plan(opportunity,profile,proposal)
    def execute(self, plan): return GuidedBrowserConnector().execute(plan)

class AdapterRegistry:
    def __init__(self): self._by_source={}; self._by_domain={}
    def register_source(self,key,adapter): self._by_source[key]=adapter
    def register_domain(self,domain,adapter): self._by_domain[domain.lower()]=adapter
    def resolve(self,source,url=''):
        if source in self._by_source:
            factory=self._by_source[source]
            if not callable(factory): return factory
            try: return factory(source)
            except TypeError: return factory()
        host=urlparse(url).hostname or ''
        for domain, factory in self._by_domain.items():
            if host==domain or host.endswith('.'+domain):
                if not callable(factory): return factory
                try: return factory(source)
                except TypeError: return factory()
        return SourceApplicationAdapter(source)

DEFAULT_ADAPTERS=AdapterRegistry()

def adapter_capabilities(registry=DEFAULT_ADAPTERS):
    return {'registered_sources':sorted(registry._by_source),'registered_domains':sorted(registry._by_domain),'default':'generic_browser'}
