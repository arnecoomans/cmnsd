from django.conf import settings
from django.utils.translation import gettext_lazy as _
import json
import traceback


class RequestMixin:
  """Reusable mixin to extract values and keys from a Django request object.

  Provides:
    - get_value_from_request(key, default=None, sources=None, silent=False)
    - get_keys_from_request(sources=None)
  
  Note: Django's CBV already sets self.request, so no setup() override needed.
  """

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
        request = getattr(self, 'request', None)
        if not request:
          self._json_body = {}
          return self._json_body
          
        body = request.body or b"{}"
        self._json_body = json.loads(body)
        # Sometimes this returns a string, and not a dict. In that case, 
        # run json.loads again to convert the string into a dict.
        if not isinstance(self._json_body, dict):
          self._json_body = json.loads(self._json_body)
      except Exception:
        self._json_body = {}
    
    return self._json_body

  def _add_message(self, text, level="debug"):
    """Safely add a message if supported."""
    if hasattr(self, "messages") and hasattr(self.messages, 'add'):
      self.messages.add(text, level)
    elif getattr(settings, 'DEBUG', False):
      print(f"[{level.upper()}] {text}")

  def get_value_from_request(self, key, default=None, sources=None, silent=False, request=None):
    """Return value of key from multiple request sources."""
    request = request or getattr(self, 'request', None)
    if not request:
      if not silent:
        self._add_message(_("No request object available"), "debug")
      return default
    
    sources = self._verify_sources(sources)
    value = None

    try:
      if "kwargs" in sources and key in getattr(self, "kwargs", {}):
        return str(self.kwargs[key]).strip()
        
      if "POST" in sources and key in request.POST:
        return str(request.POST.get(key, default)).strip()
      
      if "PATCH" in sources and hasattr(request, 'PATCH') and key in request.PATCH:
        return str(request.PATCH.get(key, default)).strip()
      
      if "json" in sources and key in self.json_body:
        return self.json_body.get(key)

      if "GET" in sources and key in request.GET:
        return str(request.GET.get(key, default)).strip()

      if "headers" in sources and self._header_key(key) in request.META:
        return request.META.get(self._header_key(key))
      
    except Exception as e:
      if getattr(settings, 'DEBUG', False):
        traceback.print_exc()
      self._add_message(_("Error fetching value: {}").format(e), "error")

    if not silent and value is None:
      msg = _("Value '{}' not found in request.").format(key)
      if default is not None:
        msg += _(" Falling back to default: '{}'").format(default)
      self._add_message(msg, "debug")

    return default

  def get_keys_from_request(self, sources=None):
    """Return all available keys from the given request sources."""
    request = getattr(self, 'request', None)
    if not request:
      return []
      
    sources = self._verify_sources(sources)
    keys = set()

    if "kwargs" in sources:
      keys |= set(getattr(self, "kwargs", {}).keys())
    if "POST" in sources:
      keys |= set(request.POST.keys())
    if "GET" in sources:
      keys |= set(request.GET.keys())
    if "PATCH" in sources and hasattr(request, 'PATCH'):
      keys |= set(request.PATCH.keys())
    if "json" in sources and isinstance(self.json_body, dict):
      keys |= set(self.json_body.keys())
    if "headers" in sources:
      keys |= {k[5:].replace("_", "-").lower() for k in request.META.keys() if k.startswith("HTTP_")}

    return list(keys)