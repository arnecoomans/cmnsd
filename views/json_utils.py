from django.conf import settings
from django.views import View
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.apps import apps
from django.db import models
from django.db.models import (
    ForeignKey,
    ManyToManyField,
    OneToOneField,
    TextField,
    CharField,
    IntegerField,
    BooleanField,
    DateField,
    DateTimeField,
    FloatField,
)

from markdown import markdown
import json


''' Import Utilities '''
from .json__utils_messages import MessageUtil
from .json__utils_security import SecurityUtil
from .json__utils_request import RequestUtil
from .json__utils_response import ResponseUtil
from .json__utils_filter import FilterUtil

class JsonUtils(MessageUtil, RequestUtil, FilterUtil, SecurityUtil, ResponseUtil, View):
  
  def __init__(self):
    self.__model = None
    self.__model_name = None
    self.__object = None
    self.__object_name = None
    self.__attributes = {}
    super().__init__()

  def dispatch(self, request, *args, **kwargs):
    # self.setup(request, *args, **kwargs)
    self.request = request
    return super().dispatch(request, *args, **kwargs)
  
  def setup(self, *args, **kwargs):
    # Run setup for super() classes
    if hasattr(super(), 'setup'):
      super().setup(*args, **kwargs)
  
 