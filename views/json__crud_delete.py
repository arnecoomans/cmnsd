from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import traceback

from .jscon__crud__util import CrudUtil
from .json_utils_meta_class import meta_field

class CrudDelete(CrudUtil):
  def crud__delete(self):
    self.verify_object()
    
    result = None
    # set the field "status" to "d" (Deleted) if the field exists
    try:
      self.obj.obj.status = "x"
      self.obj.obj.save()
      self.messages.add(_("object '{}' marked as deleted".format(self.model.name)).capitalize(), 'success')
      result = '{"info": "object marked as deleted"}'
    except Exception as e:
      if getattr(settings, "DEBUG", False):
        # Log the exception trackback to the console or log when
        # DEBUG is True in settings.py
        traceback.print_exc()
      staff_message = ': ' + str(e) if str(e) else ''
      self.messages.add(_("failed to mark object as deleted{}".format(staff_message)).capitalize(), 'error')
      raise ValueError(_("failed to mark object as deleted".capitalize()))
    return result