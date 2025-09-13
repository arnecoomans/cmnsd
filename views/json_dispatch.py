from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
import traceback
from django.conf import settings
from markdown import markdown
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import models
from django.apps import apps


from .json_utils import JsonUtil

class JsonDispatch(JsonUtil):
  ''' Meta classes for detection and dispatching
  '''
  class meta_model:
    def __init__(self, override_model=None):
      self.name = None
      self.model = None
      self.override_model = override_model
      
    def __str__(self):
      return str(self.name)

    def dispatch(self, request, *args, **kwargs):
        self.__detect()
        return super().dispatch(request, *args, **kwargs)

    def __detect(self, override_model=None):
      # Process Model Override
      if override_model or self.override_model:
        override_model = override_model or self.override_model
        if isinstance(override_model, str):
          # If a model name is supplied, detect model based on supplied name
          model_name = override_model
        elif isinstance(override_model, type) and issubclass(override_model, models.Model):
          # If a model class is supplied, use it directly
          self.name = override_model._meta.model_name
          self.model = override_model
          return
        else:
          raise ValueError(_("invalid model override").capitalize())
      else:
        model_name = override_model or self.get_value_from_request('model', default=None)
      if not model_name:
        # If still no model name is provided, raise an error
        raise ValueError(_("no model name provided in meta_model.detect()").capitalize())
      # See if model is available in installed_apps
      self.model = self.get_model_from_apps(model_name)
      self.name = self.model._meta.model_name
      return
    
    def get_model_from_apps(self, model_name):
      """ When supplied with a model name, loop through installed app models
          and return the model if a single match is found
      """
      # If the model name contains a comma, take only the first part
      if ',' in model_name:
        model_name = model_name.split(',')[0].strip()
      try:
        matching_models = []
        # Walk through all installed apps
        for app_config in apps.get_app_configs():
          # Security-measure: Skip Django's built-in apps
          secure_string = 'django.contrib.'
          if app_config.name[:len(secure_string)] == secure_string:
            continue
          # Skip models that are blocked in settings
          elif app_config.name in getattr(settings, 'JSON_BLOCKED_MODELS', []):
            continue
          try:
            # Fetch model from app_config
            model = app_config.get_model(str(model_name))
            if model:
              matching_models.append(model)
          except LookupError:
            # Model does not exist in app, skip model
            continue
        if len(matching_models) == 0:
          raise ObjectDoesNotExist(_("no model with the name '{}' could be found".format(model_name)).capitalize())
        elif len(matching_models) > 1:
          raise ObjectDoesNotExist(_("multiple models with the name '{}' were found. specify 'app_label.modelname' instead.".format({model_name})).capitalize())
      except Exception as e:
        raise ValueError(_("no model with the name '{}' could be found".format(model_name)).capitalize())
      return matching_models[0]
    
    
  
  class meta_object:
    pass

  def __init__(self, request):
    self.request = request
    self.model = None
    self.object = None
    super().__init__()

  def dispatch(self, request, *args, **kwargs):
    self.model = self.meta_model()
    self.object = self.meta_object()
    return super().dispatch(request, *args, **kwargs)
  
  
  def get_model(self):
    return False
  
  def get_object(self):
    return False
  
  
  