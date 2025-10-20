from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import PermissionDenied # , ObjectDoesNotExist, FieldDoesNotExist
# from django.db import models
from django.db.models.query import QuerySet

# from .ajax_utils import JsonUtil
from .ajax_utils_meta_model import meta_model

class meta_object():
  def __init__(self, model, qs=None, obj=None, none=True, search_mode='exact', *args, **kwargs):
    self.obj = obj if obj and isinstance(obj, model.model) else None
    self.model = model if model and isinstance(model, meta_model) else None
    self.qs = qs if isinstance(qs, QuerySet) else None
    self.identifiers = self.__get_identifiers_from_kwargs(kwargs)
    self.search_mode = str(search_mode).lower() if str(search_mode).lower() in ['exact', 'iexact', 'contains', 'icontains', 'startswith', 'istartswith'] else 'exact'
    self.none = True if none is True else False
    self.fields = []
    self.__changes = []
    self.debug_messages = []
    self.__validate()
    self.__detect()
    self.request = getattr(model, 'request', None)
    return None
  
  def __str__(self):
    if not self.obj:
      return None
    for field in ['__str__', 'name', 'title', 'slug', 'token']:
      if hasattr(self.obj, field):
        return str(getattr(self.obj, field)() if callable(getattr(self.obj, field)) else getattr(self.obj, field))
    return f"{ self.model._meta.verbose_name } object { self.obj.pk }"
    
  def __call__(self):
    return self.obj
  
  def __get_identifiers_from_kwargs(self, kwargs):
    # Store kwargs as identifiers if they have a value
    identifiers = {}
    for key, value in kwargs.items():
      if value:
        identifiers[str(key).strip()] = str(value).strip()
    return identifiers
  
  def __validate(self):
    if not self.model or not isinstance(self.model, meta_model):
      raise ValueError(_("no valid model supplied in meta_object.__init__").capitalize())

  def __detect(self):
    if self.obj:
      return self.obj
    identifiers = self.identifiers
    qs = self.qs if self.qs else self.model.model.objects.all()
    # If the model does not have a slug, add token as identifier if available in the model
    if not self.__has_field('slug') and 'slug' in identifiers and \
           self.__has_field('token') and 'token' not in identifiers:
      identifiers['token'] = identifiers.pop('slug', None)
    # Remove identifiers that are not a field of the model
    for key in list(identifiers.keys()):
      if not self.__has_field(key):
        identifiers.pop(key)
    # If no valid identifiers are left, raise an error
    if not identifiers and self.none is False:
      raise ValueError(_("no valid identifiers supplied for object lookup in model '{}'".format(self.model.name)).capitalize())
    # Ensure the queryset is searched properly according to the search_mode
    # e.g. for search_mode 'icontains', the identifier 'slug' becomes 'slug__icontains'
    identifiers = {f"{k}__{self.search_mode}": v for k, v in identifiers.items()}
    # Try to fetch the object
    if identifiers and qs:
      try:
        self.obj = qs.get(**identifiers)
        return self.obj
      except qs.model.MultipleObjectsReturned:
        raise ValueError(_("multiple objects were found for the given arguments: {}".format(identifiers)).capitalize())
      except qs.model.DoesNotExist:
        if self.model.model.objects.all().filter(**identifiers).exists():
          raise PermissionDenied(_("you do not have permission to access the requested {} with given arguments {}".capitalize().format(self.model._meta.verbose_name, ", ".join(f"{k}: {v}" for k, v in identifiers.items()))))
        raise ValueError(_("no object could be found in this querysetfor the given arguments: {}".format(", ".capitalize().join(f"{k}: {v}" for k, v in identifiers.items()))))
    # except Exception as e:
    #   staff_message = ": " + str(e) if settings.DEBUG else ""
    #   raise ValueError(_("error fetching object for the given arguments: {}{}".format(identifiers, staff_message)).capitalize())
    return None
  
  ''' Save and Commit methods '''
  def commit(self):
    if not self.obj:
      raise ValueError(_("no object to commit changes to").capitalize())
    try:
      self.obj.save()
    except Exception as e:
      staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
      raise ValueError(_("error committing changes to {} '{}': {}{}".format(self.model.name, self.obj, str(e), staff_message)).capitalize())
    return True
  
  ''' Manage Change Logging '''
  def report_change(self, change):
    self.__changes.append(change)
  def count_changes(self):
    return len(self.__changes)
  def get_changes(self):
    if len(self.__changes) == 0:
      return None
    # Create a structured representation of the changes
    structured_changes = []
    if self.count_changes() == 1:
      structured_changes.append(str(_('succesfully updated {} with the following change:'.capitalize().format(self.model.name))))
    elif self.count_changes() > 1:
      structured_changes.append(str(_('succesfully updated {} with the following {} changes:'.capitalize().format(self.model.name, str(self.count_changes())))))
    structured_changes.append('<ul>')
    for change in self.__changes:
      if 'description' in change:
        structured_changes.append(f"<li>{str(change['description'])}</li>")
      else:
        structured_changes.append(f"<li>{ _("changed field '{}' from '{}' to '{}'").format(change['field'], change['old_value'], change['new_value']) }</li>")
    structured_changes.append('</ul>')
    return "".join(structured_changes)
  
  ''' Meta methods for object state checks '''

  def is_found(self):
    return self.obj is not None
  def isfound(self):
    return self.is_found()
  
  def exists(self):
    if self.obj and self.obj.pk:
      return True
    return False

 
  
  ''' Object Field methods '''
  def __has_field(self, field):
    try:
      self.model._meta.get_field(field)
      return True
    except Exception as e:
      return False

  def list_fields(self):
    if not self.obj:
      return None
    return self.obj._meta.get_fields()
