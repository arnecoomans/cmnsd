from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, FieldDoesNotExist
from django.db import models
from django.db.models.query import QuerySet
from django.apps import apps

from .json_utils import JsonUtil

from .cmnsd_filter import FilterClass


class meta_object():
  def __init__(self, model, qs=None, obj=None, *args, **kwargs):
    self.model = model
    self.obj = obj if obj and isinstance(obj, model.model) else None
    self.qs = qs if isinstance(qs, QuerySet) else None
    self.fields = []
    self.identifiers = {}
    self.changes = {}
    # Normalize identifiers by removing empty values
    for key, value in kwargs.items():
      if value:
        self.identifiers[str(key).strip()] = str(value).strip()
    self.__detect()
    

  def __str__(self):
    if not self.obj:
      return None
    if hasattr(self.obj, '__str__'):
      object = self.obj.__str__()
    elif hasattr(self.obj, 'name'):
      object = self.obj.name
    elif hasattr(self.obj, 'slug'):
      object = self.obj.slug
    elif hasattr(self.obj, 'token'):
      object = self.obj.token
    elif hasattr(self.obj, 'id'):
      object = f"{ self.model._meta.verbose_name } #{ self.obj.id }"
    else:
      object = f"{ self.model._meta.verbose_name } object"
    return f"{ object }"
  
  def __call__(self):
    return self.obj
  
  
  def is_found(self):
    return self.obj is not None
  def isfound(self):
    return self.is_found()
  
  def exists(self):
    if self.obj and self.obj.pk:
      return True
    return False

  def is_changed(self):
    if not self.exists():
      return False
    elif self.count_changes() > 0:
      return True
    return False
  def ischanged(self):
    return self.is_changed()
  def count_changes(self):
    counter = 0
    for change in self.changes.values():
      if change.get('action') and change.get('action') != 'no change':
        counter += 1
    return counter
  
  def is_saved(self):
    if not self.exists():
      return False
    elif len(self.changes) > 0:
      return False
    return True
  def issaved(self):
    return self.is_saved()
  
  def update_simple_field(self, field, new_value=None):
    if not new_value:
      new_value = self.get_value_from_request(field)
    if new_value is None:
      raise ValueError(_("no value supplied for field '{}'".format(field)).capitalize())
    if not self.is_found():
      raise ValueError(_("no object found to change field '{}'".format(field)).capitalize())
    # Check if field is a simple field
    if not field.is_simple():
      raise ValueError(_("field '{}' is not a simple field".format(field)).capitalize())
    # Handle empty strings for non-char fields
    if new_value == "" and not isinstance(field.__field, (models.CharField, models.TextField)):
      new_value = None
    # Try to cast new_value to the correct type
    new_value = self.__cast_type(field, new_value)
    # Try to cast current value to the correct type
    new_value = self.__cast_type(field, new_value)
    # Handle choices fields
    model_field = self.model._meta.get_field(field.field_name)
    if model_field.choices:
      valid_values = [choice[0] for choice in model_field.choices]
      if new_value not in valid_values:
        # Try to get the choice value from the display label
        choice_value = self.__get_choice_value_from_display(model_field, new_value)
        if choice_value is not None:
          new_value = choice_value
        else:
          raise ValueError(_("invalid choice '{}' for field '{}'".format(new_value, field.field_name)).capitalize())
    # Get current value
    current_value = getattr(self.obj, field.field_name, None)
    if str(current_value) != str(new_value):
      setattr(self.obj, field.field_name, new_value)
      self.changes[field.field_name] = {
        'action': 'update',
        'field': field.field_name,
        'old': current_value,
        'new': new_value
      }
    else:
      self.changes[field.field_name] = {
        'action': 'no change',
        'field': field.field_name,
        'old': current_value,
        'new': new_value
      }
    return self.changes[field.field_name]

  def update_related_field(self, obj, field, related_object):
    current_objects = getattr(self.obj, field.field_name, None)
    

  def __cast_type(self, field, value):
    try:
      if isinstance(field.field(), models.IntegerField):
        value = int(value)
      elif isinstance(field.field(), models.FloatField):
        value = float(value)
      elif isinstance(field.field(), models.DecimalField):
        value = float(value)
      elif isinstance(field.field(), models.BooleanField):
        if str(value).lower() in ['true', '1', 'yes']:
          value = True
        else:
          value = False
      elif isinstance(field.field(), models.DateField):
        from django.utils.dateparse import parse_date
        value = parse_date(value)
      elif isinstance(field.field(), models.DateTimeField):
        from django.utils.dateparse import parse_datetime
        value = parse_datetime(value)
      elif isinstance(field.field(), models.EmailField):
        value = str(value).strip()
      elif isinstance(field.field(), models.URLField):
        value = str(value).strip()
      elif isinstance(field.field(), models.CharField) or isinstance(field.field(), models.TextField):
        value = str(value).strip()
    except Exception as e:
      staff_message = ": {}".format(e) if settings.DEBUG else ""
      raise ValueError(_("error casting value '{}' to correct type for field '{}'{}".format(value, field.field_name, staff_message)).capitalize())
    return value
  
  def __get_choice_value_from_display(self, field, display_value):
    """
    Convert a display label (e.g. 'Deleted') into its stored choice key (e.g. 'x').

    Args:
      field (Field): Django model field instance.
      display_value (str): The human-readable choice label.

    Returns:
      str | None: The stored choice key, or None if no match is found.
    """
    field = self.model.model._meta.get_field(field.field_name)
    for db_value, label in field.choices:
        if str(label).lower() == str(display_value).lower():
            return db_value
    return None
  
  def __has_field(self, field):
    try:
      self.model._meta.get_field(field)
      return True
    except Exception as e:
      return False
    
  def __detect(self, identifiers=None):
    if self.obj:
      return self.obj
    if not identifiers:
      identifiers = self.identifiers
    qs = self.qs if self.qs else self.model.objects.all()
    # If the model does not have a slug, add token as identifier if available in the model
    if not self.__has_field('slug') and self.__has_field('token') and 'token' not in identifiers:
      identifiers['token'] = identifiers.pop('slug', None)
    # Remove identifiers that are not a field of the model
    for key in list(identifiers.keys()):
      try:
        self.model._meta.get_field(key)
      except Exception as e:
        identifiers.pop(key)
    # If no valid identifiers are left, raise an error
    if not identifiers:
      self.obj = None
      return None
    # Try to fetch the object
    try:
      self.obj = qs.get(**identifiers)
      return self.obj
    except qs.model.MultipleObjectsReturned:
      raise ValueError(_("multiple objects were found for the given arguments: {}".format(identifiers)).capitalize())
    except qs.model.DoesNotExist:
      raise ValueError(_("no object could be found for the given arguments: {}".format(", ".join(f"{k}: {v}" for k, v in identifiers.items()))).capitalize())
    
  
  def list_fields(self):
    if not self.obj:
      return None
    return self.obj._meta.get_fields()
  

class meta_field(JsonUtil):
  def __init__(self, obj, field_name):
    self.obj = obj
    self.field_name = field_name
    self.__field = None
    self.__value = None
    self.__detect()
    self.__secure()
    self.name = field_name
    

  def __str__(self):
    return str(self.__field)

  def __call__(self):
    return self.field

  def __detect(self):
    field = None
    try:
      field = self.obj.model._meta.get_field(self.field_name)
    except Exception as e:
      # See if field is available as property
      if isinstance(getattr(self.obj.model, self.field_name, None), property):
        field = getattr(self.obj.obj, self.field_name, None)
      else:
        raise ValueError(_("no field with the name '{}' could be found in model '{}'".format(self.field_name, self.obj.model._meta.model_name)).capitalize())
    self.__field = field

  def __secure(self):
    # Security measure: ignore request of protected fields
    protected_fields = ['id', 'slug', 'status',
                        'password', 'secret_key', 'api_key', 'token', 'access_token', 'refresh_token'
                        'private_key', 'certificate'] + \
                        getattr(settings, 'AJAX_PROTECTED_FIELDS', [])
    if self.field_name in protected_fields:
      # For protected or private fields, return None
      raise PermissionDenied(_("access to field '{}' is blocked in configuration".format(self.field_name)).capitalize())
    elif hasattr(self.obj.model, 'disallow_access_fields'):
      disallowed_fields = getattr(self.obj.obj, 'disallow_access_fields', [])
      if not isinstance(disallowed_fields, list):
        disallowed_fields = [disallowed_fields]
      if self.field_name in disallowed_fields:
        raise PermissionDenied(_("access to field '{}' is blocked in model configuration".format(self.field_name)).capitalize())


  def field(self):
    return self.__field
  def get_field(self):
    return self.field()
  
  def value(self):
    if not self.__value:
      value = getattr(self.obj.obj, self.field_name, None)
      if hasattr(value, 'all') and callable(value.all):
        # If the field is a related manager, fetch all related objects
        value = value.all()
      elif callable(value):
        try:
          value = value()
        except Exception as e:
          raise ValueError(_("error occurred while calling field '{}': {}".format(self.field_name, e)).capitalize())
      self.__value = value
    return self.__value
  def get_value(self):
    return self.value()
  
  def is_foreign_key(self):
    return isinstance(self.__field, models.ForeignKey)
  def is_related(self):
    return isinstance(self.__field, (models.ManyToManyField, models.OneToOneField))
  def is_bool(self):
    return isinstance(self.__field, models.BooleanField)
  def is_simple(self):
    return isinstance(self.__field, (models.CharField, models.TextField, models.IntegerField, models.FloatField, models.DecimalField, models.DateField, models.DateTimeField, models.EmailField, models.URLField, models.BooleanField))

  def related_model(self):
    if self.is_related() or self.is_foreign_key():
      return self.__field.related_model
    return None