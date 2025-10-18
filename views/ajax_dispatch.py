from django.utils.translation import gettext_lazy as _
import traceback
from django.conf import settings
from django.apps import apps

from .ajax_utils import JsonUtil
from .json_utils_meta_model import meta_model
from .json_utils_meta_object import meta_object
from .json_utils_meta_field import meta_field
from .ajax__crud_read import CrudRead
from .ajax__crud_update import CrudUpdate
from .ajax__crud_delete import CrudDelete

''' Meta classes for detection and dispatching
'''
class JsonDispatch(JsonUtil, CrudRead, CrudUpdate, CrudDelete):    
    
  def __init__(self):
    super().__init__()
    self.model = None
    self.obj = None
    self.fields = {}
    self.modes = {'editable': False}
    
  def guess_modes(self):
    modes = {}
    for mode in ['editable', 'add']:
      # Ensure mode is set to False by default
      modes[mode] = False
      # Look for mode in GET or POST request data and set to True if found
      if mode in [key.lower() for key in self.request.GET.keys()]:
        modes[mode] = True
      elif mode in [key.lower() for key in self.request.POST.keys()]:
        modes[mode] = True
      elif self.get_value_from_request(mode, silent=True):
        modes[mode] = True
    # Return the modes dict
    return modes
  
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
      staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
      self.messages.add(_("an error occurred during request processing{}").format(staff_message).capitalize(), 'error')
      return self.return_response(status=400)
    return super().dispatch(request, *args, **kwargs)
  
  ''' Detect actions '''
  def __detect_model(self):
    if self.get_value_from_request('model', silent=True):
      try:
        self.model = meta_model(model_name=self.get_value_from_request('model'), request=self.request)
      except Exception as e:
        self.messages.add(str(e), 'error')
        return self.return_response({'error 1': str(e)}, status=400)

  def __detect_object(self):
    # Fetch Object in <str:object_id> or <str:object_slug>
    # Set identifier fields:
    available_identifiers = {
      'id': ['object_id', 'obj_id', 'object-id', 'obj-id', 'objectid', 'objid'],
      'slug': ['object_slug', 'obj_slug', 'object-slug', 'obj-slug', 'objectslug', 'objslug'],
      'token': ['object_token', 'obj_token', 'object-token', 'obj-token', 'objecttoken', 'objtoken'],
    }
    identifiers = {}
    # Check if two or more identifier types are supplied
    id_types_supplied = 0
    for id_type, id_keys in available_identifiers.items():
      for id_key in id_keys:
        if self.get_value_from_request(id_key, silent=True):
          identifiers[id_type] = self.get_value_from_request(id_key, silent=True)
          id_types_supplied += 1
          break
    if id_types_supplied > 0 and id_types_supplied < 2:
      raise ValueError(_("at least two identifiers are required for object lookup").capitalize())
    if not self.model:
      # If an invalid model is passed, this will be caught in __detect_model above
      raise ValueError(_("model is required for object lookup").capitalize())
    # Lookup object by two or more identifiers via meta_object class
    # Pass filtered queryset to meta_object to ensure security-measures are applied
    base_qs = self.model.model.objects.all()
    if hasattr(self, 'filter'):
      base_qs = self.filter(base_qs, suppress_search=True)
    self.obj = meta_object( self.model, 
                            qs=base_qs,
                            **identifiers,
                            none=True)
    return self.obj
  
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
      if self.get_value_from_request('field') == '__all__' and self.request.user.is_staff:
       # __all__ search query is only allowed for staff users
       fields = [field.name for field in self.obj.list_fields()]
      else:
        fields = [attribute.strip() for attribute in self.get_value_from_request('field').split(',')]
      for field in fields:
        # Check if field exists as attribute of object
        # if not hasattr(self.obj.obj, field):
        if not self.model.has_field(field):
          self.messages.add(_("field '{}' is not found in {} '{}'").format(field, self.model.name, self.obj).capitalize())
          continue
        self.obj.fields.append(field)
        try:
          setattr(self.obj, field, meta_field(self.obj, field))
        except Exception as e:
          # Field could not be set, so remove from requested fields
          self.obj.fields.remove(field)
          staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
          self.messages.add(_("field '{}' could not be set in {} '{}'{}").format(field, self.model.name, self.obj, staff_message).capitalize(), 'warning')

        
  ''' CRUD actions '''
  def get(self, request, *args, **kwargs):
    self.modes = self.guess_modes()
    return self.return_response(payload=self.crud__read())
  
  def post(self, request, *args, **kwargs):
    self.modes = self.guess_modes()
    return self.return_response(payload=self.crud__update())

  def patch(self, request, *args, **kwargs):
    print('PATCH request received')
    self.modes = self.guess_modes()
    return self.return_response(payload=self.crud__update())
  
  def delete(self, request, *args, **kwargs):
    self.modes = self.guess_modes()
    
    return self.return_response(payload=self.crud__delete())