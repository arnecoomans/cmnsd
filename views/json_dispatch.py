from django.utils.translation import gettext_lazy as _
import traceback
from django.conf import settings
from django.apps import apps

from .json_utils import JsonUtil
from .json_utils_meta_class import meta_model, meta_field, meta_object
from .json__crud_read import CrudRead
''' Meta classes for detection and dispatching
'''
class JsonDispatch(JsonUtil, CrudRead):    
    
  def __init__(self):
    self.model = None
    self.obj = None
    self.fields = {}
    super().__init__()

  def dispatch(self, request, *args, **kwargs):
    try:
      # Detect model based on request data
      self.__detect_model()
      # Detect object based on request data if model is detected
      self.__detect_object()
      # Detect fields based on request data if object is detected
      self.__detect_fields()
    except Exception as e:
      # Exception Handling
      if getattr(settings, "DEBUG", False):
        # Log the exception trackback to the console or log when
        # DEBUG is True in settings.py
        traceback.print_exc()
      self.messages.add(str(e), 'error')
      return self.return_response(status=400)
    return super().dispatch(request, *args, **kwargs)
  
  ''' Detect actions '''
  def __detect_model(self):
    if self.get_value_from_request('model', silent=True):
      try:
        self.model = meta_model(self.get_value_from_request('model'))
      except Exception as e:
        return self.return_response({'error 1': str(e)}, status=400)

  def __detect_object(self):
    # Fetch Object in <str:object_id> or <str:object_slug>
    if self.get_value_from_request('object_id', silent=True) or \
        self.get_value_from_request('object_slug', silent=True):
      if not self.model:
        # Should not occur due to urls.py requirement of model
        return self.return_response({'error 2': _("model is required for object lookup").capitalize()}, status=400)
        raise ValueError(_("model is required for object lookup").capitalize())
      # Lookup object by ID or slug via meta_object class, allowing for empty ID or slug
      # Pass filtered queryset to meta_object to ensure security-measures are applied
      self.obj = meta_object( self.model.model, 
                              qs=self.filter(self.model.model.objects.all()),
                              id=self.get_value_from_request('object_id', silent=True), 
                              slug=self.get_value_from_request('object_slug', silent=True))
  
  def __detect_fields(self):
    # Fetch Field in <str:field>
    if self.get_value_from_request('field', silent=True):
      if not self.obj:
        if not self.model:
          # If an invalid model is passed, this will be caught in __detect_object above
          self.messages.add(_("model is required for field lookup").capitalize(), 'error')
        else:
          # If invalid object is passed, this will be caught in __detect_object above
          self.messages.add(_("object is required for field lookup").capitalize(), 'error')
        # Stop processing and return errors
        return self.return_response(status=400)
      # Handle special field values: show all fields when __all__ is passed
      if self.get_value_from_request('field') == '__all__':
       fields = [field.name for field in self.obj.list_fields()]
      else:
        fields = [attribute.strip() for attribute in self.get_value_from_request('field').split(',')]
      for field in fields:
        # Check if field exists as attribute of object
        if not hasattr(self.obj.obj, field):
          self.messages.add(_("field '{}' is not found in {} '{}'").format(field, self.model.name, self.obj).capitalize())
          continue
        self.obj.fields.append(field)
        try:
          setattr(self.obj, field, meta_field(self.obj, field))
        except Exception as e:
          # Field could not be set, so remove from requested fields
          self.obj.fields.remove(field)
          self.messages.add(_("field '{}' could not be set in {} '{}': {}").format(field, self.model.name, self.obj, e).capitalize(), 'warning')
        
  ''' CRUD actions '''
  def get(self, request, *args, **kwargs):
    return self.return_response(payload=self.crud__read())
  
  def post(self, request, *args, **kwargs):
    return self.return_response({'info': 'POST method not yet implemented'}, status=501)
