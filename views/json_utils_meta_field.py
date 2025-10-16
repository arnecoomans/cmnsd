from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, FieldDoesNotExist
from django.db import models
from django.db.models.query import QuerySet
from django.apps import apps
from uuid import UUID
import traceback
import json

class meta_field:
  def __init__(self, obj, field_name):
    self.obj = obj
    self.field_name = field_name
    self.__field = None
    self.__value = None
    self.__detect()
    self.__secure()
    self.name = field_name
    self.request = getattr(obj, 'request', None)
    return None
    
  ''' Meta methods for field information '''
  def __str__(self):
    return str(self.__field)

  def __call__(self):
    return self.field

  
  def __detect(self):
    """
    Detect and assign the corresponding field or property for the given field name.

    This method attempts to resolve ``self.field_name`` to either:
      1. A Django model field defined in the model's ``_meta`` metadata, or
      2. A Python property defined directly on the model class.

    If the field cannot be resolved through either method, a ``ValueError`` is raised.

    The resolved field or property object is stored internally in ``self.__field``.

    Raises:
      ValueError: If no matching model field or property can be found for
                  ``self.field_name``.

    Example:
      ```python
      # Assuming self.field_name = "status"
      self.__detect()
      print(self.__field)  # <django.db.models.fields.CharField: status>
      ```

    Notes:
      - Database fields are resolved via ``model._meta.get_field()``.
      - If the field does not exist in the model schema, the method checks if it
        is defined as a ``@property`` on the model class.
      - The resolved field or property is not returned directly but stored in
        ``self.__field`` for later use.
    """
    field = None
    try:
      field = self.obj.model._meta.get_field(self.field_name)
    except FieldDoesNotExist:
      # See if field is available as property
      if isinstance(getattr(self.obj.model, self.field_name, None), property):
        field = getattr(self.obj.obj, self.field_name, None)
      else:
        raise ValueError(_("no field with the name '{}' could be found in model '{}'".format(self.field_name, self.obj.model._meta.model_name)).capitalize())
    self.__field = field

  def __secure(self):
    """
    Enforce field-level access restrictions for AJAX-based updates.

    This method prevents unauthorized access to sensitive or protected fields
    that should never be modified or exposed through AJAX requests.

    It performs two checks:
      1. **Global Protection** — blocks access to known sensitive fields such as
        ``id``, ``slug``, ``password``, ``token`` etc., including any additional
        fields defined in ``settings.AJAX_PROTECTED_FIELDS``.
      2. **Model-Specific Protection** — blocks access to fields listed in the
        model’s ``disallow_access_fields`` property or method.

    Raises:
      PermissionDenied: If the requested field name is protected either globally
                        or at the model level.

    Example:
      ```python
      # Assuming self.field_name = "password"
      self.__secure()  # Raises PermissionDenied
      ```

    Notes:
      - Global protected fields can be extended in Django settings:
          AJAX_PROTECTED_FIELDS = ['session_token', 'api_secret']
      - Model-level protection allows dynamic field restrictions per model.
    """
    # Define default protected fields (always restricted)
    conf_protected = getattr(settings, 'AJAX_PROTECTED_FIELDS', [])
    if not isinstance(conf_protected, (list, tuple, set)):
      conf_protected = [conf_protected]
    protected_fields = [
      'id', 'slug', 'status',
      'password', 'secret_key', 'api_key', 'token',
      'access_token', 'refresh_token', 'private_key', 'certificate',
    ] + conf_protected

    # Global protection check
    if self.field_name in protected_fields:
      raise PermissionDenied(
        _("access to field '{}' is blocked in configuration")
          .format(self.field_name).capitalize()
      )

    # Model-specific protection check
    if hasattr(self.obj.model, 'disallow_access_fields'):
      disallowed_fields = getattr(self.obj.obj, 'disallow_access_fields', [])
      if not isinstance(disallowed_fields, (list, tuple)):
        disallowed_fields = [disallowed_fields]
      if self.field_name in disallowed_fields:
        raise PermissionDenied(
          _("access to field '{}' is blocked in model configuration")
            .format(self.field_name).capitalize()
        )
  

  ''' Meta methods for field information '''
  def field(self):
    return self.__field
  def get_field(self):
    return self.field()
  
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
    value = getattr(self.obj.obj, self.field_name, None)

    # Case 1: Related manager (e.g. ManyToMany or reverse FK)
    if hasattr(value, "all") and callable(value.all):
      try:
        value = value.all()
      except Exception as e:
        staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
        raise ValueError(
          _("error occurred while fetching related objects for field '{}'{}")
            .format(self.field_name, staff_message).capitalize()
        )

    # Case 2: Callable property (method or computed attribute)
    elif callable(value):
      try:
        value = value()
      except Exception as e:
        staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
        raise ValueError(
          _("error occurred while calling field '{}'{}")
            .format(self.field_name, staff_message).capitalize()
        )

    # Cache the resolved value
    self.__value = value
    self._value_cached = True

    return self.__value
  def get_value(self):
    """ Alias for value() method. """
    return self.value()
  

  """ Field type checks """
  def is_foreign_key(self):
    return isinstance(self.__field, models.ForeignKey)
  def is_related(self):
    return isinstance(self.__field, (models.ManyToManyField, models.OneToOneField, models.ManyToOneRel))
  def is_bool(self):
    return isinstance(self.__field, models.BooleanField)
  def is_simple(self):
    return isinstance(self.__field, (models.CharField, models.TextField, models.IntegerField, models.FloatField, models.DecimalField, models.DateField, models.DateTimeField, models.EmailField, models.URLField, models.BooleanField))
  def get_type(self):
    return self.__field.__class__.__name__
  def related_model(self):
    """
    Return the related model class for this field, if applicable.

    This method determines whether the current field represents a relationship
    (e.g. ForeignKey, OneToOneField, or ManyToManyField) and returns the related
    model class that the field points to. It gracefully handles cases where helper
    methods such as `is_related()` or `is_foreign_key()` are not defined.

    Returns:
      Model | None: The related Django model class if the field is relational,
                    otherwise `None`.

    Example:
      >>> field.related_model()
      <class 'app.models.Category'>

    Implementation details:
      - Uses `is_related()` or `is_foreign_key()` if available.
      - Falls back to inspecting Django’s `remote_field.model` metadata.
      - Returns `None` for non-relational fields or when metadata is incomplete.
    """
    try:
      # Case 1: Use helper methods if they exist
      if hasattr(self, "is_related") and callable(self.is_related):
        if self.is_related():
          return getattr(self.__field, "related_model", None)

      if hasattr(self, "is_foreign_key") and callable(self.is_foreign_key):
        if self.is_foreign_key():
          return getattr(self.__field, "related_model", None)

      # Case 2: Fallback — detect relation through Django internals
      if hasattr(self.__field, "remote_field") and getattr(self.__field.remote_field, "model", None):
        return self.__field.remote_field.model

      # Default: no related model
      return None

    except AttributeError:
      # Gracefully handle incomplete metadata or misconfigured fields
      return None
    except Exception as e:
      # Log or debug error only in development mode
      if getattr(settings, "DEBUG", False):
        import traceback
        traceback.print_exc()
      return None
  def get_related_model(self):
    """ Alias for related_model() method. """
    return self.related_model()
  

  ''' Field Value Management '''
  def has_display(self):
    """
    Check if a model field has a display value available (i.e. it defines `choices`).

    Args:
      obj (models.Model): The model instance.
      field_name (str): Name of the field to check.

    Returns:
      bool: True if the field has a display method or defined choices, False otherwise.
    """
    try:
      field = self.obj.obj._meta.get_field(self.field_name)
      display_method = getattr(self.obj.obj, f"get_{self.field_name}_display", None)
      if self.__field.choices:
        return True
      elif callable(display_method):
        return True
    except Exception as e:
      pass
    return hasattr(self.obj, f"get_{self.field_name}_display")


  def get_display(self, value=None):
    """
    Retrieve the display label for a given field's stored value.

    If the field defines choices, this returns the human-readable label.
    If the field has no choices, it simply returns the raw value.

    Args:
      obj (models.Model): The model instance.
      field_name (str): The name of the field.
      value (Any, optional): The stored value. If not provided, the value is read from the object.

    Returns:
      Any: The human-readable display label if available, otherwise the stored value.

    Raises:
      ValueError: If the field does not exist or display resolution fails.
    """
    try:
      # If Django auto-generated a get_<field>_display method, use it only when no value is supplied
      display_method = getattr(self.obj.obj, f"get_{self.field_name}_display", None)
      if callable(display_method) and not value:
        return display_method()

      # Fallback: manually map value to label via field.choices
      field = self.obj.obj._meta.get_field(self.field_name)
      if field.choices:
        choices_dict = dict(field.choices)
        return choices_dict.get(value, value)

    except Exception as e:
      if getattr(settings, "DEBUG", False):
        import traceback; traceback.print_exc()
      staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
      raise ValueError(
        _("could not resolve display value for field '{}' with value '{}'{}")
          .format(self.field_name, value, staff_message)
          .capitalize()
      )

    # Default fallback — return raw value
    return value

  def __cast_type(self, value, field=None):
    """
    Attempt to cast an input value to the appropriate Python type
    based on the model field definition.

    This function ensures incoming values (from JSON, form, or query data)
    are coerced into types compatible with their corresponding Django model fields.

    Args:
      field (FieldWrapper): A wrapped model field object providing access to `.field()`
                            and `.field_name`.
      value (Any): The raw input value to cast.

    Returns:
      Any: The correctly typed and sanitized value.

    Raises:
      ValueError: If the value cannot be safely cast to the target type.

    Supported conversions:
      - IntegerField → int
      - FloatField / DecimalField → float
      - BooleanField → bool (`true`, `1`, `yes` → True)
      - DateField → `datetime.date`
      - DateTimeField → `datetime.datetime`
      - EmailField / URLField / CharField / TextField → str (trimmed)
    """
    if not field:
      field = self.__field

    try:
      if value is None or value == '':
        return '' if isinstance(field, (models.CharField, models.TextField)) else None
      
      # Integer and numeric types
      if isinstance(field, models.IntegerField):
        value = int(value)

      elif isinstance(field, (models.FloatField, models.DecimalField)):
        value = float(value)

      # Boolean fields (tolerant conversion)
      elif isinstance(field, models.BooleanField):
        if str(value).lower() in ["true", "1", "yes", "on"]:
          value = True
        elif str(value).lower() in ["false", "0", "no", "off"]:
          value = False
        else:
          raise ValueError(_("invalid boolean value '{}'").format(value))

      # Date / datetime types
      elif isinstance(field, models.DateField):
        from django.utils.dateparse import parse_date
        value = parse_date(value)

      elif isinstance(field, models.DateTimeField):
        from django.utils.dateparse import parse_datetime
        value = parse_datetime(value)

      # String-based fields
      elif isinstance(field, (models.EmailField, models.URLField, models.CharField, models.TextField)):
        value = str(value).strip()

      elif isinstance(field, models.JSONField):
        if isinstance(value, str):
          try:
            value = json.loads(value)
          except json.JSONDecodeError:
            raise ValueError(_("invalid JSON value for field '{}'").format(field.name))

      elif isinstance(field, models.UUIDField):
        value = UUID(str(value))


      # Unhandled field types pass through unchanged
      else:
        value = value

    except Exception as e:
      staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
      raise ValueError(
        _("error casting value '{}' to correct type for field '{}'{}")
          .format(value, self.name, staff_message)
          .capitalize()
      )

    return value
  
  def __normalize_choices(self, value):
    """
    Normalize a display or stored value for fields with choices.

    If the field defines choices and the provided value corresponds
    to a display label (e.g. "Published"), this method returns the
    stored value (e.g. "p"). If the value already matches a valid
    stored value, it is returned unchanged.

    For fields without choices, the original value is always returned.

    Args:
      value (Any): The input value to normalize.

    Returns:
      Any: The stored (database) value corresponding to the input,
          or the input value itself if no normalization was needed.

    Raises:
      ValueError: If the field defines choices but the provided value
                  is neither a valid stored value nor a display label.
    """
    # If the field has no display (i.e. no choices), return the value unchanged
    if not hasattr(self, "has_display") or not callable(self.has_display) or not self.has_display():
      return value

    try:
      # Get the model field definition from Django metadata
      model_field = self.obj.obj._meta.get_field(self.field_name)
      choices = getattr(model_field, "choices", None)

      if not choices:
        return value

      # Build lookup dictionaries
      value_map = {str(k): k for k, _ in choices}           # stored value lookup
      display_map = {str(v).lower(): k for k, v in choices} # display label lookup

      # Direct match with stored value (quick path)
      if str(value) in value_map:
        return value_map[str(value)]

      # Match by display label (case-insensitive)
      lower_value = str(value).lower()
      if lower_value in display_map:
        return display_map[lower_value]

      # If no match found, raise a descriptive error
      raise ValueError(
        _("invalid choice '{}' for field '{}'").format(value, self.field_name).capitalize()
      )

    except Exception as e:
      if getattr(settings, "DEBUG", False):
        traceback.print_exc()
      # Gracefully return the original value when unsure (safe default)
      return value

  """ Field Modification methods """
  def update_simple(self, new_value):
    """
    Update a simple (non-relational) field with a new value.

    This method ensures that only "simple" fields (e.g., CharField, IntegerField, BooleanField, etc.)
    are updated, performs automatic type casting, detects changes, and reports updates
    using the object's change reporting mechanism (`obj.report_change()`).

    Args:
      new_value (Any): The new value to assign to the field.

    Raises:
      ValueError: If the field is not a simple field or type casting fails.
      AttributeError: If the wrapped object or field is improperly initialized.

    Returns:
      bool: True if the value was successfully updated, False otherwise.
    """
    # Verify value type:
    if not self.is_simple():
      raise ValueError(_("cannot update {}'s simple field '{}' with value '{}' because value does not belong to a {}").capitalize().format(self.obj().name, self.field_name, str(new_value), 'simple field'))
    # Type cast according to the field definition
    new_value = self.__cast_type(new_value)
    new_value = self.__normalize_choices(new_value)
    # Fetch the current stored value
    old_value = self.value()
    # Skip update if the new value is effectively unchanged
    if str(new_value) == str(old_value):
      return False
    # Apply the change
    setattr(self.obj.obj, self.field_name, new_value)
    self.__value = new_value
    # Report the change
    self.obj.report_change({
      'field': self.name, 
      'old_value': self.get_display(old_value) if self.has_display() else old_value,
      'new_value': self.get_display(new_value) if self.has_display() else new_value,
    })
    # Return success
    return True
    
  
  def update_foreign_key(self, related_identifiers):
    # Verify value type:
    if not self.is_foreign_key():
      raise ValueError(_("cannot update {}'s foreign key field '{}' with value '{}' because value does not belong to a {}").capitalize().format(self.obj().name, self.field_name, str(related_identifiers), 'foreign key field'))
    # Check for related model
    if not self.related_model():
      raise ValueError(_("cannot update {}'s foreign key field '{}' with value '{}' because related model could not be determined").capitalize().format(self.obj().name, self.field_name, str(related_identifiers)))
    # Find related object based on related_identifiers
    related_obj = self.__get_related_object(related_identifiers)
    current_value = self.value()
    if not related_obj:
      related_obj = self.__create_related_object(related_identifiers)
    # If related object is already set, remove it
    if self.value() == related_obj:
      pass
    else:
      # Set value to new related object
      try:
        setattr(self.obj.obj, self.field_name, related_obj)
        self.__value = related_obj
        self.obj.report_change({
          'field': self.name, 
          'old_value': str(current_value),
          'new_value': str(related_obj),
        })
      except Exception as e:
        staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
        return ValueError(_("unable to set value of {} to {}{}").capitalize().format(str(self.field_name), str(related_obj), staff_message))
    return True
  
  def update_related(self, related_identifiers):
    # Verify value type:
    if not self.is_related():
      raise ValueError(_("cannot update {}'s related field '{}' with value '{}' because value does not belong to a {}").capitalize().format(self.obj().name, self.field_name, str(related_identifiers), 'related field'))
    # Check for related model
    if not self.related_model():
      raise ValueError(_("cannot update {}'s related field '{}' with value '{}' because related model could not be determined").capitalize().format(self.obj().name, self.field_name, str(related_identifiers)))
    # Find related object based on related_identifiers
    related_obj = self.__get_related_object(related_identifiers)
    current_value = self.value()
    if not related_obj:
      related_obj = self.__create_related_object(related_identifiers)
    # If related object is already set, remove it
    if isinstance(current_value, QuerySet) and related_obj in current_value:
      # Remove related object from object field
      try:
        getattr(self.obj.obj, self.field_name).remove(related_obj)
        self.__value = related_obj
        self.obj.report_change({
          'field': self.name, 
          'old_value': str(current_value),
          'new_value': str(related_obj),
          'description': _("removed '{}' '{}' from {} {}").capitalize().format(str(related_obj._meta.verbose_name), str(related_obj), str(self.obj.model._meta.verbose_name), str(self.obj.obj)),
        })
      except Exception as e:
        staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
        return ValueError(_("unable to remove value of {} to {}{}").capitalize().format(str(self.field_name), str(related_obj), staff_message))
    else:
      # Add related object to object field
      try:
        getattr(self.obj.obj, self.field_name).add(related_obj)
        self.__value = related_obj
        self.obj.report_change({
          'field': self.name, 
          'old_value': str(current_value),
          'new_value': str(related_obj),
          'description': _("added '{}' '{}' to '{}' '{}'").capitalize().format(str(related_obj._meta.verbose_name), str(related_obj), str(self.obj.model._meta.verbose_name), str(self.obj.obj)),
        })
      except Exception as e:
        staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
        return ValueError(_("unable to add value of {} to {}{}").capitalize().format(str(self.field_name), str(related_obj), staff_message))
    return True

  ''' Foreign Key / Related Object Handling '''
  def __get_related_object(self, identifiers, search_method='iexact', model=None, depth=0):
    """
    Fetch a related object based on provided identifiers.

    Automatically resolves nested related objects (dict values) before lookup.
    If a related object cannot be found, this function returns None rather than raising.

    Args:
      identifiers (dict): A dictionary of field lookups (e.g. {'id': 3, 'slug': 'foo'}).
      search_method (str): Comparison operator, defaults to 'iexact'.
      model (Model): Optional explicit model to search in.
      depth (int): Current recursion depth (for nested relations).

    Returns:
      Optional[Model]: The related object if found, or None if not found.

    Raises:
      ValueError: For invalid identifier formats or multiple matches.
      RecursionError: If recursion exceeds AJAX_MAX_DEPTH_RECURSION.
    """
    target_model = model or self.related_model()
    max_depth = getattr(settings, "AJAX_MAX_DEPTH_RECURSION", 3)

    if not isinstance(identifiers, dict):
        raise ValueError(
            _("invalid identifier format for related object lookup: {}").format(str(identifiers)).capitalize()
        )

    if depth >= max_depth:
        raise RecursionError(
            _("maximum recursion depth ({}) exceeded while resolving related objects for model '{}'").format(
                max_depth, target_model.__name__
            ).capitalize()
        )

    # --- Resolve nested relations first ---
    resolved_identifiers = {}
    for key, value in identifiers.items():
        if isinstance(value, dict):
            try:
                related_field = target_model._meta.get_field(key)
                if getattr(related_field, "is_relation", False):
                    nested_model = related_field.related_model
                    nested_obj = (
                        self.__get_related_object(value, model=nested_model, depth=depth + 1)
                        or self.__create_related_object(value, model=nested_model, depth=depth + 1)
                    )
                    resolved_identifiers[key] = nested_obj
                    continue
            except Exception as e:
                if getattr(settings, "DEBUG", False):
                    print(f"[DEBUG] Failed to resolve nested relation '{key}' on {target_model}: {e}")
        resolved_identifiers[key] = value

    # --- Perform actual lookup ---
    try:
        return target_model.objects.get(**resolved_identifiers)
    except target_model.DoesNotExist:
        return None
    except target_model.MultipleObjectsReturned:
        raise ValueError(
            _("multiple related objects were found for the given arguments: {}").format(resolved_identifiers).capitalize()
        )
    except Exception as e:
        staff_message = f": {e}" if getattr(settings, "DEBUG", False) or self.request.user.is_superuser else ""
        raise ValueError(
            _("error fetching related {} object for the given arguments: {}{}")
              .format(target_model.__name__, resolved_identifiers, staff_message)
              .capitalize()
        )


  def __create_related_object(self, identifiers, model=None, depth=0):
    """
    Create a new instance of the related model using provided identifiers.
    Supports parent:child creation if the model has a 'parent' field.
    Automatically resolves nested related objects from dict values.

    Args:
      identifiers (dict): A dictionary of creation attributes.
      model (Model): Optional model to create (defaults to self.related_model()).
      depth (int): Current recursion depth.

    Returns:
      Model: The created (or found) related object.

    Raises:
      PermissionDenied: If creation is not allowed by settings.
      RecursionError: If recursion exceeds AJAX_MAX_DEPTH_RECURSION.
      ValueError: For invalid identifiers or database errors.
    """
    related_model = model or self.related_model()
    related_model_name = str(related_model._meta.verbose_name).lower()
    max_depth = getattr(settings, "AJAX_MAX_DEPTH_RECURSION", 3)

    if depth >= max_depth:
        raise RecursionError(
            _("maximum recursion depth ({}) exceeded while creating related objects for model '{}'").format(
                max_depth, related_model.__name__
            ).capitalize()
        )

    # --- Security checks ---
    if self.is_foreign_key() and related_model_name not in getattr(settings, "AJAX_ALLOW_FK_CREATION_MODELS", []):
        raise PermissionDenied(
            _("creation of new related objects is not allowed for foreign key field '{}'").format(related_model_name).capitalize()
        )

    if self.is_related() and related_model_name not in getattr(settings, "AJAX_ALLOW_RELATED_CREATION_MODELS", []) \
       and not getattr(settings, "AJAX_ALLOW_RELATED_CREATION_MODELS", False) == True:
        raise PermissionDenied(
            _("creation of new related objects is not allowed for related field '{}'").format(related_model_name).capitalize()
        )

    # --- Add user if applicable ---
    defaults = {}
    if self.request.user.is_authenticated and hasattr(related_model, "user"):
        defaults["user"] = self.request.user if "user" not in identifiers else identifiers["user"]

    # --- Handle parent:child name pattern ---
    if "name" in identifiers and ":" in str(identifiers["name"]):
        return self.__create_with_parents(related_model, identifiers["name"], defaults)

    # --- Resolve nested related objects ---
    resolved_identifiers = {}
    for key, value in identifiers.items():
        if isinstance(value, dict):
            try:
                related_field = related_model._meta.get_field(key)
                if getattr(related_field, "is_relation", False):
                    nested_model = related_field.related_model
                    nested_obj = (
                        self.__get_related_object(value, model=nested_model, depth=depth + 1)
                        or self.__create_related_object(value, model=nested_model, depth=depth + 1)
                    )
                    resolved_identifiers[key] = nested_obj
                    continue
            except Exception as e:
                if getattr(settings, "DEBUG", False):
                    print(f"[DEBUG] Failed to resolve nested relation '{key}' on {related_model}: {e}")
        resolved_identifiers[key] = value

    # --- Create object normally ---
    try:
        related_obj = related_model.objects.create(**{**defaults, **resolved_identifiers})
        related_obj.save()

        self.obj.report_change({
            "field": self.name,
            "old_value": None,
            "new_value": str(related_obj),
            "description": _("created new '{}' '{}'").capitalize().format(
                str(related_obj._meta.verbose_name), str(related_obj)
            ),
        })
        return related_obj

    except Exception as e:
        staff_message = f": {e}" if getattr(settings, "DEBUG", False) or self.request.user.is_superuser else ""
        raise ValueError(
            _("error creating new related object for the given arguments: {}{}")
              .capitalize()
              .format(identifiers, staff_message)
        )


  def __create_with_parents(self, related_model, full_name, defaults=None):
    """
    Recursively resolve or create parent-child objects from a colon-separated string.

    Example:
      "swimming:heated pool" → ensures parent 'swimming' exists,
      then creates/gets 'heated pool' with parent='swimming'.

    Args:
      related_model (Model): The related model class to work with.
      full_name (str): The colon-separated object name chain.
      defaults (dict): Optional default field values for creation (e.g., user).

    Returns:
      models.Model: The deepest created or retrieved object (the child).
    """
    from django.utils.text import slugify

    # Prepare parts and validate
    parts = [p.strip() for p in str(full_name).split(":") if p.strip()]
    if not parts:
        raise ValueError(_("invalid name '{}': no valid parts found").format(full_name).capitalize())

    field_names = [f.name for f in related_model._meta.get_fields()]

    # No parent field? → just create the full object directly
    if "parent" not in field_names:
        identifiers = {"name": full_name}
        if "slug" in field_names:
            identifiers["slug"] = slugify(full_name)
        if defaults:
            identifiers.update(defaults)
        return self.__get_related_object(identifiers) or self.__create_related_object(identifiers)

    # Recursive parent creation
    parent_obj = None
    for part in parts:
        identifiers = {"name": part}
        if "slug" in field_names:
            identifiers["slug"] = slugify(part)
        if parent_obj:
            identifiers["parent"] = parent_obj
        if defaults:
            identifiers.update(defaults)

        # Try to find parent first
        found = self.__get_related_object(identifiers, search_method='iexact')
        if found:
            parent_obj = found
            continue

        # If not found, create it
        parent_obj = self.__create_related_object(identifiers)

    return parent_obj
