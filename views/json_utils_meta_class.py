from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import models
from django.db.models.query import QuerySet
from django.apps import apps

from .json_utils import JsonUtil
from .cmnsd_filter import FilterClass

class meta_model(JsonUtil):
  def __init__(self, model=None):
    self.name = None
    self.model = None
    self.__detect(model=model)
    self.__secure()
    
  def __str__(self):
    return str(self.name)
  
  def __call__(self):
    return self.model

  def __detect(self, model=None):
    if not model:
      raise ValueError(_("no model supplied in JsonDispatch.meta_model.__init__").capitalize())
    # See if model is available in installed_apps
    self.model = self.get_model_from_apps(model)
    self.name = self.model._meta.model_name
    return
  
  def __secure(self):
    # Security-measure: Check if model is blocked in settings
    if self.model._meta.app_label in getattr(settings, 'JSON_BLOCKED_MODELS', []):
      raise PermissionDenied(_("access to model '{}' is blocked".format(self.name)).capitalize())
    return
  
  def get_model_from_apps(self, model_name):
    """
    When supplied with a model name (singular class name or plural verbose name),
    loop through installed app models and return the model if a single match is found.
    """
    if "," in model_name:
      model_name = model_name.split(",")[0].strip()

    search_name = str(model_name).lower()
    matching_models = []

    for app_config in apps.get_app_configs():
      secure_string = "django.contrib."
      if app_config.name.startswith(secure_string):
        continue
      elif app_config.name in getattr(settings, "JSON_BLOCKED_MODELS", []):
        continue

      # First try direct class-name match
      try:
        model = app_config.get_model(search_name)
        if model:
          matching_models.append(model)
          continue
      except LookupError:
        pass

      # Then try plural verbose_name match
      for model in app_config.get_models():
        if model._meta.verbose_name_plural.lower() == search_name:
          matching_models.append(model)

    if len(matching_models) == 0:
      raise ObjectDoesNotExist(
        _("no model with the name '{}' could be found").format(model_name).capitalize()
      )
    elif len(matching_models) > 1:
      raise ObjectDoesNotExist(
        _("multiple models with the name '{}' were found. specify 'app_label.modelname' instead.").format(model_name).capitalize()
      )
    return matching_models[0]


class meta_object():
  def __init__(self, model, qs=None, *args, **kwargs):
    self.model = model
    self.obj = None
    self.qs = qs if isinstance(qs, QuerySet) else None
    self.fields = []
    self.identifiers = {}
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
    return f"{ object }"
  
  def __call__(self):
    return self.obj
  
  def __detect(self, identifiers=None):
    if not identifiers:
      identifiers = self.identifiers
    qs = self.qs if self.qs else self.model.objects.all()
    try:
      self.obj = qs.get(**identifiers)
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
                        getattr(settings, 'JSON_PROTECTED_FIELDS', [])
    if self.field_name in protected_fields:
      # For protected or private fields, return None
      raise PermissionDenied(_("access to field '{}' is blocked in configuration".format(self.field_name)).capitalize())
    elif hasattr(self.obj.model, 'disallow_access_fields'):
      disallowed_fields = getattr(self.obj.model, 'disallow_access_fields', [])
      if self.field_name in disallowed_fields:
        raise PermissionDenied(_("access to field '{}' is blocked in model configuration".format(self.field_name)).capitalize())

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
    