from django.conf import settings
from django.utils.translation import gettext_lazy as _
import json
import traceback


class RequestMixin:
  """Reusable mixin to extract values and keys from a Django request object.

  Provides:
    - setup(request, *args, **kwargs)
    - get_value_from_request(key, default=None, sources=None, silent=False)
    - get_keys_from_request(sources=None)
  """

  def setup(self, request, *args, **kwargs):
    """Attach request object and call parent setup if available."""
    if not hasattr(self, "request"):
      self.request = request
    if hasattr(super(), "setup"):
      super().setup(request, *args, **kwargs)

  def _verify_sources(self, sources=None):
    """Normalize and validate request data sources."""
    default_sources = getattr(settings, "AJAX_DEFAULT_DATA_SOURCES", ["kwargs", "GET", "POST", "json", "headers"])
    if not sources:
      return default_sources
    if isinstance(sources, str):
      sources = [sources]
    invalid = [s for s in sources if s not in default_sources]
    if invalid:
      raise ValueError(_("Invalid source(s): {}").format(", ".join(invalid)))
    return sources

  def _header_key(self, key):
    """Convert key to HTTP_ format for META lookup."""
    return f"HTTP_{key.replace('-', '_').upper()}"

  @property
  def json_body(self):
    """Return parsed JSON body (cached)."""
    if not hasattr(self, "_json_body"):
      try:
        self._json_body = json.loads(self.request.body or "{}")
        # Sometimes this returns a string, and not a dict. In that case, 
        # run json.loads again to convert the string into a dict.
        if type(self._json_body) is not dict:
          self._json_body = json.loads(self._json_body)
      except Exception:
        self._json_body = {}
    
    return self._json_body

  def _add_message(self, text, level="debug"):
    """Safely add a message if supported."""
    if hasattr(self, "messages"):
      self.messages.add(text, level)

  def get_value_from_request(self, key, default=None, sources=None, silent=False, request=None):
    request = getattr(self, 'request', None) if request is None else request
    """Return value of key from multiple request sources."""
    sources = self._verify_sources(sources)
    value = None

    try:
      if "kwargs" in sources and key in getattr(self, "kwargs", {}):
        return str(self.kwargs[key]).strip()
      if request:
        if "POST" in sources and key in request.POST:
          return str(request.POST.get(key, default)).strip()
        
        if "PATCH" in sources and key in request.PATCH:
          return str(request.PATCH.get(key, default)).strip()
        
        if "json" in sources and key in self.json_body:
          return self.json_body.get(key)

        if "GET" in sources and key in request.GET:
          return str(request.GET.get(key, default)).strip()

        if "headers" in sources and self._header_key(key) in request.META:
          return request.META.get(self._header_key(key))
      
    except Exception as e:
      traceback.print_exc()
      self._add_message(_("Error fetching value: {}").format(e), "error")

    if not silent:
      msg = _("Value '{}' not found in request.").format(key)
      if default is not None:
        msg += _(" Falling back to default: '{}'").format(default)
      self._add_message(msg, "debug")

    return default

  def get_keys_from_request(self, sources=None):
    """Return all available keys from the given request sources."""
    sources = self._verify_sources(sources)
    keys = set()

    if "kwargs" in sources:
      keys |= set(getattr(self, "kwargs", {}).keys())
    if "POST" in sources:
      keys |= set(self.request.POST.keys())
    if "GET" in sources:
      keys |= set(self.request.GET.keys())
    if "PATCH" in sources:
      keys |= set(self.request.PATCH.keys())
    if "json" in sources and isinstance(self.json_body, dict):
      keys |= set(self.json_body.keys())
    if "headers" in sources:
      keys |= {k[5:].replace("_", "-").lower() for k in self.request.META.keys() if k.startswith("HTTP_")}

    return list(keys)