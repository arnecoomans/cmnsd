from django.conf import settings
from django.utils.translation import gettext_lazy as _
import traceback

from .ajax__crud__util import CrudUtil
from .ajax_utils_meta_object import meta_object
from .ajax_utils_meta_field import meta_field

class CrudUpdate(CrudUtil):

  def crud__update(self):
    # Retrieve payload data and map this to object usable fields 
    # (field__subfield is mapped to field)
    self.update_results = []
    payload = self._get_payload()
    # Get the object referenced by the request
    obj = self._get_obj()
    actions = self._get_actions(obj, payload)
    if getattr(settings, 'DEBUG', False):
      print("UPDATE OBJECT:", self.obj, "of model", self.model)
      print("PAYLOAD:", payload)
      print("ACTIONS:", actions)
    # Update fields in a safe order: simple, bool, foreign_key, related
    try:
      self.__update_simple_fields(obj, actions)
      self.__update_foreign_key_fields(obj, actions)
      obj.commit()
      self.__update_related_fields(obj, actions)
      if obj.count_changes() > 0:
        self.messages.add(obj.get_changes(), 'success')
    except ValueError as e:
      self.messages.add(str(e), 'error')
    except Exception as e:
      staff_message = ''
      if getattr(settings, 'DEBUG', False):
        staff_message = ': ' + str(e)
        traceback.print_exc()
      self.messages.add(_("an unexpected error occured when updating fields of {}{}").capitalize().format(str(obj), staff_message), 'error')
    # self.__process_changes(obj)
    self.modes = self.guess_modes()
    return self.crud__read()
    
  def _get_payload(self, max_depth=3):
    """
    Build a structured payload dictionary from request data, 
    with configurable maximum nesting depth.

    Keys containing double-underscores (``__``) are grouped into nested
    dictionaries up to the specified depth. Beyond that depth, remaining parts
    are concatenated back into a flattened key.

    Example:
      Input:
        {
          "name": "Example",
          "settings__theme": "dark",
          "settings__ui__color__shade": "blue"
        }

      Output (max_depth=1):
        {
          "name": "Example",
          "settings": {
            "theme": "dark",
            "ui__color__shade": "blue"
          }
        }

      Output (max_depth=2):
        {
          "name": "Example",
          "settings": {
            "theme": "dark",
            "ui": {
              "color__shade": "blue"
            }
          }
        }

    Args:
      max_depth (int): Maximum depth to group nested keys. 
                       Depth=0 completely flat, 
                       Depth=1 top-level grouping only (default).

    Returns:
      dict: A structured dictionary grouped according to ``max_depth``.

    Raises:
      ValueError: If malformed or empty keys are encountered.

    Notes:
      - Request sources are determined by ``get_sources()``.
      - Values are retrieved via ``get_value_from_request()``.
      - Malformed keys are skipped and logged using ``self.messages``.
    """
    payload = {}
    sources = self.get_sources()
    keys = self.get_keys_from_request(sources=sources)

    for key in keys:
        # Skip empty or malformed keys
        if not key or key.startswith('__') or key.endswith('__'):
            self.messages.add(
                _("Malformed key '{}' skipped while building payload.").format(key),
                "debug"
            )
            continue

        value = self.get_value_from_request(key, sources=sources, silent=True)

        # Split key into components
        parts = key.split('__')
        if len(parts) == 1 or max_depth == 0:
            # Completely flat or no nesting requested
            payload[parts[0]] = value
            continue

        # Determine grouping level based on max_depth
        group_parts = parts[:max_depth]
        remainder = '__'.join(parts[max_depth:])

        # Navigate or create group structure up to max_depth
        current = payload
        for i, part in enumerate(group_parts):
            # Final depth reached → store the remaining part(s)
            if i == len(group_parts) - 1:
                if remainder:
                    # Ensure group is a dict
                    if part not in current or not isinstance(current[part], dict):
                        current[part] = {}
                    current[part][remainder] = value
                else:
                    current[part] = value
            else:
                # Intermediate level
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]

    return payload


  
  def _get_obj(self):
    """
    Ensure a valid object (`self.obj`) is available for the current CRUD operation.

    If no object exists or the existing object is not marked as found, this method
    delegates creation to `__create_obj()`.

    Returns:
      meta_object: A `meta_object` instance wrapping the resolved or newly created model object.

    Raises:
      ValueError: If the model is invalid or object creation fails.
    """
    if not self.model or not hasattr(self.model, "model"):
      raise ValueError(_("invalid model metadata — cannot initialize object").capitalize())

    # Check whether an existing object is available
    if not self.obj or not getattr(self.obj, "is_found", lambda: False)():
      # Create a new object when none exists
      self.obj = self.__create_obj()

    return self.obj


  def __create_obj(self):
    """
    Create and wrap a new model instance in a `meta_object`.

    This method safely instantiates a new unsaved object for the current model
    and records the creation event in `self.update_results`. It does *not* save
    the object to the database — this responsibility remains with the caller.

    Returns:
      meta_object: A newly created `meta_object` instance wrapping the unsaved model instance.

    Raises:
      ValueError: If the model cannot be instantiated.
    """
    try:
      # Instantiate the model safely
      instance = self.model.model()

      # Wrap the instance inside a meta_object
      obj = meta_object(self.model, obj=instance)

      # Record creation in update log
      self.update_results.append({
        "action": "create",
        "field": "object",
        "old": str(self.obj) if getattr(self, "obj", None) and getattr(self.obj, "obj", None) else None,
        "new": getattr(self.model, "name", str(self.model)),
      })

      return obj

    except Exception as e:
      traceback.print_exc()
      raise ValueError(
        _("could not initialize object for model '{}': {}")
          .format(getattr(self.model, "name", str(self.model)), e)
          .capitalize()
      )

  def _clean_related_dict(self, d: dict):
    """
    Remove empty or meaningless keys from a related-field dict.
    Return None if nothing meaningful remains.
    """
    if not isinstance(d, dict):
        return d

    cleaned = {k: v for k, v in d.items() if v not in ("", None)}
    return cleaned or None
  
  ''' get_actions:
      Return the actions to be performed on the object based on the payload and requested fields
  '''
  def _get_actions(self, obj, payload):
    actions = {
      'simple': {},
      'foreign_key': {},
      'related': {},
    }
    # Check if fields are passed in the request
    if len(obj.fields) == 0:
      # No fields are passed in the request, so walk through the payload
      # and map existing object fields to the object meta class
      for key in payload.keys():
        if self.model.has_field(key):
          # Field is a field of the model/object, so add it to the object meta class
          obj.fields.append(key)
          setattr(obj, key, meta_field(obj, key, self.request))
    # Map request fields to payload values
    for field in obj.fields:
      if field in payload.keys():
        # Request Field has a Payload Value. Add to Actionable Fields
        if type(payload[field]) is dict:
          value = self._clean_related_dict(payload[field])
          if value is not None:
            payload[field] = value
          else:
            continue
        if self.__get_update_type(field) not in actions:
          actions[self.__get_update_type(field)] = {}
        actions[self.__get_update_type(field)][field] = payload[field]
      else:
        if getattr(settings, 'DEBUG', False):
          print("[DEBUG] Field '{}' in object fields {} but not in payload keys {}.".format(field, obj.fields, list(payload.keys())))
    return actions
    
  def __get_update_type(self, field):
    if getattr(self.obj, field).is_simple():
      return 'simple'
    elif getattr(self.obj, field).is_bool():
      return 'simple'
    elif getattr(self.obj, field).is_foreign_key():
      return 'foreign_key'
    elif getattr(self.obj, field).is_related():
      return 'related'
    else:
      staff_message = ': ' + getattr(self.obj, field).get_type() if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
      raise ValueError(_("field '{}' is of an unsupported type for update{}".capitalize().format(str(field), staff_message)))
  


  ''' UPDATE FIELD FUNCTIONS '''

  def __update_simple_fields(self, obj, actions):
    for field, value in actions['simple'].items():
      # Verify field is updatable
      if not hasattr(obj, field):
        raise ValueError(_("field '{}' does not exist on object {} '{}'".format(field, self.model.name, obj)).capitalize())
      # self.__update_simple_field(obj, field, new_value=value)
      getattr(self.obj, field).update_simple(value)

  def __update_foreign_key_fields(self, obj, actions):
    for field, value in actions['foreign_key'].items():
      # Verify field is updatable
      if not hasattr(obj, field):
        raise ValueError(_("field '{}' does not exist on object {} '{}'".format(field, self.model.name, obj)).capitalize())
      getattr(self.obj, field).update_foreign_key(value)

  def __update_related_fields(self, obj, actions):
    for field, value in actions['related'].items():
      # Verify field is updatable
      if not hasattr(obj, field):
        raise ValueError(_("field '{}' does not exist on object {} '{}'".format(field, self.model.name, obj)).capitalize())
      getattr(self.obj, field).update_related(value)