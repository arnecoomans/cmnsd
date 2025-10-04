from django.conf import settings
from django.utils.translation import gettext_lazy as _
import json
import traceback

''' Configuration options 
  - json_request_default_data_sources: 
      ['kwargs', 'GET', 'POST', 'json', 'headers']
      Default sources to search for the value.
  - json_request_new_value_keys: 
      ['set_id', 'get_id', 'obj_id', 'set_slug', 'get_slug', 'obj_slug', 'value', 'set_value', 'get_value', 'obj_value']
      New value keys contain new values for opbjects. Since slug, id, 
      pk already refer to the object, these cannot be used as keys.
'''
class RequestUtil:
  def __init__(self):
    super().__init__()
  
  def setup(self, request, *args, **kwargs):
    # Run setup for SecurityUtil
    if not hasattr(self, 'request'):
      self.request = request
    # Call the setup method of the superclass if it exists
    if hasattr(super(), 'setup'):
      super().setup(request, *args, **kwargs)

  def __verify_sources(self, sources=None):
    ''' Verify sources content and format '''
    if not sources:
      sources = getattr(settings, 'AJAX_DEFAULT_DATA_SOURCES', ['kwargs', 'GET', 'POST', 'json', 'headers'])
    if not isinstance(sources, list):
      sources = [sources]
    return sources

  def __get_header_key(self, key):
    """ Returns the header key for a given key. """
    return f"HTTP_{key.replace('-', '_').upper()}"

  def get_value_from_request(self, key, default=None, sources=None, silent=False):
    """ Returns the value of KEY from the request object. 
        Searches the sources for the value, sources should be a list of strings.
    """
    sources = self.__verify_sources(sources)
    # Prepare value placeholder
    value = None
    ''' Json data requires a special treatment,
        because the request body is not parsed by default.
        We need to parse the request body to get the json data.
        This is done by using the json library.
    '''
    if 'json' in sources:
      # Try to fetch json data from the request
      jsondata = {}
      try:
        jsondata = json.loads(self.request.body)
      except:
        # Fail silently
        pass
    ''' Validate sources to loop through 
        Sources should be a list of strings
        Valid sources are: kwargs, GET, POST, json, headers
    '''
    default_sources = getattr(settings, 'AJAX_DEFAULT_DATA_SOURCES', ['kwargs', 'GET', 'POST', 'json', 'headers'])
    if not isinstance(sources, list):
      sources = [sources]
    if len(sources) == 0:
      sources = default_sources
    for source in sources:
      if source not in default_sources:
        raise ValueError(_("source {} is not valid").format(source).capitalize())
    try:
      # Loop through sources to find the value.
      # As soon as there is a match in the sources, return the value.
      # That means that a value can be submitted by one source only.
      if 'kwargs' in sources and key in self.kwargs:
        value = self.kwargs[key]
      if 'POST' in sources and  key in self.request.POST:
        value = self.request.POST.get(key, None)
      if 'json' in sources and key in jsondata:
        value = jsondata.get(key)
      if 'GET' in sources and key in self.request.GET:
        value = self.request.GET.get(key, None)
      if 'headers' in sources and  self.__get_header_key(key) in self.request.META:
        value = self.request.META.get(self.__get_header_key(key), None)
    except Exception as e:
      self.messages.add(_("error when fetching value: {}").format(str(e)).capitalize(), "debug")
      traceback.print_exc()
    if value is None and default is not None and not silent:
      self.messages.add(_("value \"{}\" not found in request, falling back to default: \"{}\"").format(str(key), str(default)).capitalize(), "debug")
    elif value is None and not silent:
      self.messages.add(_("value \"{}\" not found in request").format(str(key)).capitalize(), "debug")
    # Return value as string without leading/trailing whitespace
    return str(value).strip() if value else default
  
  def get_keys_from_request(self, default=None, sources=None):
    """ Returns the keys from the request object. 
        Searches the sources for the keys, sources should be a list of strings.
    """
    sources = self.__verify_sources(sources)
    keys = []
    if 'kwargs' in sources:
      keys += list(self.kwargs.keys())
    if 'POST' in sources:
      keys += list(self.request.POST.keys())
    if 'GET' in sources:
      keys += list(self.request.GET.keys())
    if 'json' in sources:
      # Try to fetch json data from the request
      jsondata = {}
      try:
        jsondata = json.loads(self.request.body)
        if isinstance(jsondata, dict):
          keys += list(jsondata.keys())
      except:
        # Fail silently
        pass
    if 'headers' in sources:
      keys += [key[5:].replace('_', '-').lower() for key in self.request.META.keys() if key.startswith('HTTP_')]
    # Remove duplicates by converting to a set and back to a list
    keys = list(set(keys))
    if len(keys) == 0 and default is not None:
      return default
    return keys