from django.conf import settings
from django.views import View
from django.utils.translation import gettext_lazy as _
from django.apps import apps

from markdown import markdown


''' Import Utilities '''
from .ajax__utils_messages import MessageUtil
from .ajax__utils_request import RequestUtil
from .ajax__utils_response import ResponseUtil

from .cmnsd_filter import FilterClass

class JsonUtil(MessageUtil, RequestUtil, ResponseUtil, FilterClass, View):
  
  def __init__(self):
    super().__init__()

  def dispatch(self, request, *args, **kwargs):
    # self.setup(request, *args, **kwargs)
    self.request = request
    return super().dispatch(request, *args, **kwargs)
  
  def setup(self, *args, **kwargs):
    # Run setup for super() classes
    if hasattr(super(), 'setup'):
      super().setup(*args, **kwargs)
  
 