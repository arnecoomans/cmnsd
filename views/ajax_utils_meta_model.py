from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, FieldDoesNotExist
from django.apps import apps
from django.db import models
from django.db.models.base import ModelBase


# from .ajax_utils import JsonUtil
# from .cmnsd_filter import FilterMixin

class meta_model:
  def __init__(self, model_name=None, request=None):
    self.name = None
    self.model = None
    self.__detect(model_name=model_name)
    self.__secure()
    self._meta = self.model._meta
    self.request = request
    return None
  
  def __str__(self):
    return str(self.name)
  
  def __call__(self):
    return self.model

  def __detect(self, model_name=None, model=None):
    # If model is supplied directly, use it
    if model and isinstance(model, models.Model) and hasattr(model, 'model'):
      # Object instance is supplied, use its model as model definition
      self.model = model.model
    elif model and isinstance(model, ModelBase):
      # Model class is supplied, use it directly
      self.model = model
    else:
      # Model name is supplied, look up model in installed apps
      self.model = self.get_model_from_apps(model_name)
    self.name = self.model._meta.model_name
    return
  
  def __secure(self):
    # Security-measure: Check if model is blocked in settings
    if self.model._meta.app_label in getattr(settings, 'AJAX_BLOCKED_MODELS', []) or \
      self.name in getattr(settings, 'AJAX_BLOCKED_MODELS', []):
      raise PermissionDenied(_("access to model '{}' is blocked in application configuration".format(self.name)).capitalize())
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
      elif app_config.name in getattr(settings, "AJAX_BLOCKED_MODELS", []):
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
  

  def has_field(self, field):
    """
    Check whether the current model defines a given field.

    This method safely determines if the model associated with this instance
    includes a field with the specified name. It uses Django's model metadata
    (`_meta`) for lookup and returns a boolean result instead of raising an
    exception.

    Args:
      field (str): The name of the field to check.

    Returns:
      bool: ``True`` if the field exists on the model, otherwise ``False``.

    Example:
      ```python
      if self.has_field("slug"):
          print("This model has a slug field.")
      ```

    Notes:
      - Internally, this wraps ``self.model._meta.get_field(field)`` in a
        try/except block to prevent exceptions from propagating.
      - It will return ``False`` for both missing fields and invalid field names.
    """
    try:
      self.model._meta.get_field(field)
      return True
    except FieldDoesNotExist:
      return False
