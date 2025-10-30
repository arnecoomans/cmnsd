from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, FieldDoesNotExist
from django.db import models
from django.db.models.query import QuerySet
from django.apps import apps
from uuid import UUID
import traceback
import json
import inspect


class meta_function:
  def __init__(self, obj, function_name, request=None):
    self.request = getattr(obj, 'request', request)
    self.obj = obj
    self.function_name = function_name
    self._function = None
    self._value = None
    self._detect()
    self._secure()
    self.name = function_name
    return None
    
  ''' Meta methods for field information '''
  def __str__(self):
    return str(self._get_value())

  def __call__(self):
    return self.__function()

  
  def _detect(self):
    function = None
    if not self.obj.model.has_function(self.function_name):
      raise ValueError(_("'{}' is not a valid function of model '{}'".format(self.function_name, self.model.name).capitalize()))
    try:
      function = getattr(self.obj.obj, self.function_name)
    except AttributeError as e:
      staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
      raise ValueError(_("no function with the name '{}' could be found in object of type '{}'{}".format(self.function_name, type(self.obj), staff_message).capitalize()))
    self._function = function
    self._value = function()
    
  def _secure(self):
    return True
  
  def value(self):
    """
    Resolve and return the current value of the field associated with this object.

    This method dynamically retrieves the value of ``self.field_name`` from the
    model instance ``self.obj.obj``. It handles different types of field values:
    
    - **Direct fields**: Returns the field value directly.
    - **Related managers**: If the field represents a reverse relation (e.g.
      ``ManyToManyField``), returns a queryset via ``.all()``.
    - **Callable attributes**: If the field is a callable (e.g. a property method),
      executes the callable and returns its result.

    The resolved value is cached in ``self.__value`` for subsequent calls.

    Returns:
      Any: The resolved field value, or ``None`` if the field does not exist.

    Raises:
      ValueError: If the callable field raises an exception during execution.

    Example:
      ```python
      # For a related manager:
      tags = handler.value()  # Returns <QuerySet [...]>

      # For a callable property:
      name_display = handler.value()
      ```

    Notes:
      - The result is cached to avoid redundant database hits or computations.
      - If the field value is a callable that requires arguments, it will not be
        executed automatically and will raise an error if called incorrectly.
    """
    # Return cached value if already resolved
    if hasattr(self, "_value_cached") and self._value_cached:
      return self.__value

    # Default to None if the attribute does not exist
    value = getattr(self.obj.obj, self.function_name, None)

    # Case 1: Related manager (e.g. ManyToMany or reverse FK)
    if hasattr(value, "all") and callable(value.all):
      try:
        value = value.all()
      except Exception as e:
        staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
        raise ValueError(
          _("error occurred while fetching related objects for field '{}'{}")
            .format(self.function_name, staff_message).capitalize()
        )

    # Case 2: Callable property (method or computed attribute)
    elif callable(value):
      try:
        # Attempt to call with `request` if function supports it
        try:
          print("A")
          value = value(request=self.request)
        except TypeError as e:
          # Retry without request if it’s not accepted
          if "unexpected keyword argument 'request'" in str(e):
            print("B")
            value = value()
          else:
            print("C")
            raise e
      except Exception as e:
        staff_message = (
          ": " + str(e)
          if getattr(settings, "DEBUG", False) or getattr(self.request.user, "is_superuser", False)
          else ""
        )
        raise ValueError(
          _("error occurred while calling function '{}'{}")
            .format(self.field_name, staff_message)
            .capitalize()
        )

    # Cache the resolved value
    self.__value = value
    self._value_cached = True

    return self.__value
  def get_value(self):
    """ Alias for value() method. """
    return self.value()