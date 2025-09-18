from django.conf import settings
from django.utils.translation import gettext_lazy as _
import json

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

  def dispatch(self, request, *args, **kwargs):
    return super().dispatch(request, *args, **kwargs)
  
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
      sources = getattr(settings, 'json_request_default_data_sources', ['kwargs', 'GET', 'POST', 'json', 'headers'])
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
    default_sources = getattr(settings, 'json_request_default_data_sources', ['kwargs', 'GET', 'POST', 'json', 'headers'])
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
      elif 'POST' in sources and  key in self.request.POST:
        value = self.request.POST.get(key, None)
      elif 'json' in sources and key in jsondata:
        value = jsondata.get(key)
      elif 'GET' in sources and key in self.request.GET:
        value = self.request.GET.get(key, None)
      elif 'headers' in sources and  self.__get_header_key(key) in self.request.META:
        value = self.request.META.get(self.__get_header_key(key), None)
    except Exception as e:
      self.messages.add(_("error when fetching value: {}").format(str(e)).capitalize(), "debug")
    if value is None and default is not None and not silent:
      self.messages.add(_("value \"{}\" not found in request, falling back to default: \"{}\"").format(str(key), str(default)).capitalize(), "debug")
    elif value is None and not silent:
      self.messages.add(_("value \"{}\" not found in request").format(str(key)).capitalize(), "debug")
    # Return value as string without leading/trailing whitespace
    return str(value).strip() if value else default
  

  # def get_new_value(self, field=None):
  #   # Get the value for the request parameters. 
  #   # The value can be stored in get, post or
  #   # query parameters, and can be id, slug or value.
  #   if self.new_value:
  #     if field in self.new_value.keys():
  #       return self.new_value[field]
  #     return self.new_value
  #   # Loop through the possible keys to get the value
  #   new_value_keys = getattr(settings, 'json_request_new_value_keys',
  #                            ['set_id', 'get_id', 'obj_id',
  #                            'set_slug', 'get_slug', 'obj_slug',
  #                            'value', 'set_value', 'get_value', 'obj_value']
  #                            )
  #   for key in new_value_keys:
  #     value = self.get_value_from_request(key, False)
  #     if value:
  #       for word in ['set', 'get', 'obj']:
  #         key = key.replace(f"{ word }_" , '')  
  #       self.new_value = {'key': key, 'value': value,}
  #       return self.get_new_value(field) # Recursively call the function to get the value if field is specified
  #   raise ValueError(_("no valid identifier found in new value").capitalize())