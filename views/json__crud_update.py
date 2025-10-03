from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import traceback

from .jscon__crud__util import CrudUtil
from .json_utils_meta_class import meta_field

class CrudUpdate(CrudUtil):
  def crud__update(self):
    self.verify_object()
    field = self.get_field(self)
    field = self.validate_field(field)
    result = None
    # Update the field based on the field type
    try:
      if field.is_bool():
        result = self.__update_bool(field)
      elif field.is_foreign_key():
        result = self.__update_foreign_key(field)
      elif field.is_related():
        result = self.__update_related_field(field)
      else:
        result = self.__update_simple_field(field)
    except Exception as e:
      if getattr(settings, "DEBUG", False):
        traceback.print_exc()
      staff_message = ': ' + str(e) if self.request.user.is_staff else ""
      self.messages.add(_("error occurred during update") + staff_message, 'error')
      self.status = 400
    return {field.field_name: self.render_field(field.field_name)}
    
  # def __verify_object(self):
  #   if not self.model:
  #     raise ValueError(_("no model detected for update").capitalize())
  #   elif not self.obj:
  #     raise ValueError(_("no object detected for update").capitalize())
  #   return True
  
  # def __get_field(self, sources=None):
  #   field = False
  #   # Check if field is supplied in request URL (kwargs)
  #   if self.obj.fields:
  #     # Assume first field if multiple fields are supplied
  #     field = self.obj.fields[0]
  #     if self.obj.fields.__len__() > 1:
  #       self.messages.add(_("multiple fields were supplied but only one is supported").capitalize() + ". " + _("using first field '{}'").format(field).capitalize(), 'warning')
  #   else:
  #     # Check if field is supplied in request data (POST or JSON)
  #     fields = self.get_keys_from_request(sources=self.__get_sources())
  #     for f in fields:
  #       if self.model.is_field(f):
  #         field = f
  #         # Only use the first valid field found, assume the rest are value identifiers
  #         break
  #   if not field:
  #     raise ValueError(_("no valid field supplied for update").capitalize())
  #   return field
  
  # def __validate_field(self, field):
  #   if hasattr(self.obj, field):
  #     # Field exists as attribute of object and is already loaded
  #     return getattr(self.obj, field)
  #   elif self.model.is_field(field):
  #     # Field exists as attribute of object but is not yet loaded
  #     try:
  #       value = meta_field(self.obj, field)
  #       return value
  #     except Exception as e:
  #       staff_message = ': ' + str(e) if self.request.user.is_staff else ""
  #       raise ValueError(_("field '{}' could not be retrieved from {} '{}'{}".format(field, self.model.name, self.obj, staff_message)).capitalize())
  #   else:
  #     raise ValueError(_("field '{}' is not found in {} '{}'".format(field, self.model.name, self.obj)).capitalize())
  
  def __get_value(self, field, identifier=None, allow_none=False):
    value = None
    # Check if value is supplied in request data (POST or JSON) (ex. ?name=Foo)
    if identifier and self.get_value_from_request(identifier, silent=True, sources=self.__get_sources()):
      value = self.get_value_from_request(identifier, sources=self.__get_sources())
    elif self.get_value_from_request(field.field_name, silent=True, sources=self.__get_sources()):
      value = self.get_value_from_request(field.field_name, sources=self.__get_sources())
    elif self.get_value_from_request('value', silent=True, sources=self.__get_sources()):
      value = self.get_value_from_request('value', sources=self.__get_sources())
    if not allow_none and value is None:
      raise ValueError(_("no value supplied for field '{}'".format(field)).capitalize())
    return value
  
  def __update_field(self, field, value, old_value=None):
    if value is None:
      raise ValueError(_("no value supplied for field '{}'".format(field)).capitalize())
    try:
      setattr(self.obj.obj, field.field_name, value)
      self.obj.obj.save()
      if old_value is not None and str(old_value) != str(value):
        self.messages.add(_("field '{}' in {} '{}' successfully changed from '{}' to '{}'".format(field.name, self.model.name, self.obj, old_value, value)).capitalize(), 'success')
      else:
        self.messages.add(_("field '{}' in {} '{}' successfully updated to '{}'".format(field.name, self.model.name, self.obj, value)).capitalize(), 'success')
      return True
    except Exception as e:
      staff_message = ': ' + str(e) if self.request.user.is_staff else ""
      self.messages.add(_("field '{}' in {} '{}' could not be updated to '{}'{}".format(field.name, self.model.name, self.obj, value, staff_message)).capitalize(), 'error')
      return False
    
  def __get_sources(self):
    sources = ['json', 'POST']
    if getattr(settings, 'DEBUG', False):
      sources.append('GET')
    return sources
  
  ''' Update methods for different field types '''

  def __update_foreign_key(self, field):
    print('UPDATING FOREIGN KEY FIELD:', field.field_name)
    """
    Update a ForeignKey field on the current object.

    This function attempts to resolve a related object for the given
    ForeignKey field using the value provided in the request. It ensures
    that the relation is resolved in a case-insensitive manner and applies
    additional filtering logic if `self.filter` is defined.

    Args:
      field (models.ForeignKey): The ForeignKey field to update.

    Returns:
      object: Result of calling `__update_field` with the resolved object.

    Raises:
      ValueError: If no value is supplied, if no object can be found,
                  if multiple objects match the input, or if another
                  error occurs while filtering.
    """
    # Resolve the related model once and reuse
    related_model = field.related_model()

    # Get field identifier from request
    # Identifier is any field of the related model except the field name itself mentioned in the request
    # example: /category/?editable&slug=foo - identifier is 'slug' for field 'category' since field "editable" 
    # does not exist in Category model
    identifier = None
    for key in self.get_keys_from_request(sources=self.__get_sources()):
      if key != field.field_name and key in [f.name for f in related_model._meta.get_fields()]:
        identifier = key
        break

    # Get the value supplied by the request. Do not allow None values.
    value = self.__get_value(field, identifier=identifier, allow_none=False)

    try:
      # Start with all objects of the related model
      qs = related_model.objects.all()

      # If a custom filter() method exists on this class, apply it
      if hasattr(self, 'filter'):
        qs = self.filter(qs, suppress_search=True)

      # Lookup by identifier or primary key (case-insensitive)
      pk_name = identifier if identifier else related_model._meta.pk.name
      value = qs.get(**{f"{pk_name}__iexact": value})

    # Raised if more than one object matches the filter
    except related_model.MultipleObjectsReturned:
      raise ValueError(
        _("multiple objects were found for the given arguments: {}")
          .format({pk_name: value})
          .capitalize()
      )

    # Raised if no object matches the filter
    except related_model.DoesNotExist:
      raise ValueError(
        _("no object could be found for the given arguments: {}")
          .format({pk_name: value})
          .capitalize()
      )

    # Any other error (e.g. invalid lookup, DB error, etc.)
    except Exception as e:
      staff_message = ': ' + str(e) if self.request.user.is_staff else ""
      raise ValueError(
        _("error occurred while filtering related model '{}' with {}='{}'{}")
          .format(related_model, pk_name, value, staff_message)
          .capitalize()
      )

    # Defensive check: ensure a value was actually provided
    if value is None:
      raise ValueError(
        _("no value supplied for field '{}'").format(field).capitalize()
      )

    # Perform the update on the field with the resolved related object
    return self.__update_field(field, value)


  from django.utils.text import slugify

  def __create_with_parents(self, related_model, full_name, user=None):
    """
    Recursively resolve or create an object (and its parents) from a
    colon-separated name string.

    - If the object already exists, its parent is not modified.
    - If a parent exists, its parent chain is respected (not overwritten).
    - If the model has a 'slug' field, lookup is first attempted by slug,
      otherwise by name.
    - When creating new objects, slug is generated via slugify(name).

    Example:
      "foo:bar" → ensures "foo" exists, then gets/creates "bar" with parent=foo
      "one:foo:bar" → ensures "one" exists, then "foo" (parent=one),
                      then "bar" (parent=foo)

    Args:
      related_model (Model): The Django model to resolve/create.
      full_name (str): Colon-separated name string.
      user (User|None): Optional user to assign if the model has a 'user' field.

    Returns:
      object: The resolved or newly created object.
    """
    parts = full_name.split(":")
    field_names = [f.name for f in related_model._meta.get_fields()]

    # If no parent field exists → create or get full object directly
    if "parent" not in field_names:
      slug = slugify(full_name) if "slug" in field_names else None
      lookup = {"slug": slug} if slug else {"name": full_name}
      kwargs = {"name": full_name}
      if slug:
        kwargs["slug"] = slug
      if user and "user" in field_names:
        kwargs["user"] = user
      obj, created = related_model.objects.get_or_create(defaults=kwargs, **lookup)
      if created:
        self.messages.add(
          _("a new {} '{}' was created").format(related_model._meta.model_name, obj).capitalize(),
          "info"
        )
      return obj

    parent = None
    for part in parts:
      slug = slugify(part) if "slug" in field_names else None

      # Lookup prefers slug if available
      lookup = {"slug": slug} if slug else {"name": part}
      if parent:
        lookup["parent"] = parent

      try:
        obj = related_model.objects.get(**lookup)
      except related_model.DoesNotExist:
        # Create new object
        kwargs = {"name": part}
        if slug:
          kwargs["slug"] = slug
        if user and "user" in field_names:
          kwargs["user"] = user
        if parent:
          kwargs["parent"] = parent
        obj = related_model.objects.create(**kwargs)

      parent = obj  # move one step deeper

    return parent


  def __resolve_related_object(self, field, identifiers):
    """
    Resolve (or create) a related object for a field.

    - Tries to fetch the related object from the database.
    - Looks up by slug (if the related model has a slug field) or by name,
      case-insensitive.
    - If the object does not exist:
        * Checks if it exists outside the filtered queryset (and is blocked).
        * Otherwise, attempts to create it, injecting `user` if the model
          supports it.
    - Does NOT handle parent chains (that is done in __create_with_parents).

    Args:
      field (models.ForeignKey | models.ManyToManyField): The related field.
      identifiers (dict): A dictionary of lookup values (e.g. {"slug": "foo"}).

    Returns:
      object: The resolved or newly created related object.

    Raises:
      ValueError: If multiple objects match, if object exists but is unavailable,
                  or if creation fails.
    """
    related_model = field.related_model()
    qs = related_model.objects.all()
    # Remove None/False values from identifiers
    identifiers = {k: v for k, v in identifiers.items() if v not in (None, False)}

    # Apply filtering if available
    if hasattr(self, "filter"):
      qs = self.filter(qs, suppress_search=True)

    try:
      # Case-insensitive lookup on all identifiers
      lookup = {f"{k}__iexact": v for k, v in identifiers.items()}
      return qs.get(**lookup)

    except related_model.MultipleObjectsReturned:
      raise ValueError(
        _("multiple objects were found for the given arguments: {}")
          .format(identifiers).capitalize()
      )

    except related_model.DoesNotExist:
      # Check if object exists outside the filtered queryset
      simple_lookup = {}
      field_names = [f.name for f in related_model._meta.get_fields()]
      if "slug" in identifiers and "slug" in field_names:
        simple_lookup["slug__iexact"] = identifiers["slug"]
      elif "id" in identifiers and "id" in field_names:
        simple_lookup["id"] = identifiers["id"]
      else:
        simple_lookup = {f"{k}__iexact": v for k, v in identifiers.items()}
      if related_model.objects.filter(**simple_lookup).exists():
        raise ValueError(
          _("the object with argument '{}' exists, but is not available")
            .format(simple_lookup).capitalize()
        )

      # Attempt to create object
      if self.model.is_field("user"):
        if not self.request.user or not self.request.user.is_authenticated:
          raise ValueError(
            _("the object with argument '{}' does not exist and could not be created: {}")
              .format(identifiers, _("user is not authenticated").capitalize()).capitalize()
          )
        identifiers["user"] = self.request.user
      
      try:
        # Always slugify slug if model has slug field - make sure slug input is slugified
        if 'slug' in field_names:
          if 'slug' in identifiers:
            identifiers['slug'] = slugify(identifiers['slug'])
          elif 'name' in identifiers:
            identifiers['slug'] = slugify(identifiers['name'])
          else:
            identifiers['slug'] = slugify(next(iter(identifiers.values())))
        
        # Create the object with the given identifiers
        obj = related_model.objects.create(**identifiers)
        self.messages.add(
          _("a new {} '{}' was created")
            .format(related_model._meta.model_name, obj).capitalize(),
          "info"
        )
        return obj
      except Exception as e:
        staff_message = ': ' + str(e) if self.request.user.is_staff else ""
        raise ValueError(
          _("the object with argument '{}' does not exist and could not be created{}")
            .format(identifiers, staff_message).capitalize()
        )

    except Exception as e:
      staff_message = ': ' + str(e) if self.request.user.is_staff else ""
      raise ValueError(
        _("error occurred while filtering related model '{}' with identifiers {}{}")
          .format(related_model, identifiers, staff_message).capitalize()
      )


  def __update_related_field(self, field):
    """
    Update a ManyToMany-related field on the current object.

    Resolves a related object using request data, then toggles its
    membership in the relation: removes it if already present, adds it if not.

    Args:
      field (models.ManyToManyField): The related field to update.

    Returns:
      QuerySet | bool: The updated related field queryset if successful,
                      or False if an error occurred.

    Raises:
      ValueError: If no identifiers are provided or object resolution fails.
    """
    identifiers = {}
    # Collect identifiers from request (excluding the field name itself)
    model_fields = [f.name for f in field.related_model()._meta.get_fields()]
    for key in self.get_keys_from_request(sources=self.__get_sources()):
      if key != field.field_name:
        if key in model_fields:
          identifiers[key] = self.get_value_from_request(key, sources=self.__get_sources())

    # Remove identifiers with empty values
    identifiers = {k: v for k, v in identifiers.items() if v not in (None, False, '')}
    
    # Ensure at least one identifier is provided
    if len(identifiers) == 0:
      raise ValueError(
        _("no identifiers supplied for related field '{}'").format(field.field_name).capitalize()
      )

    # Special handling: recursive parent creation when "name" contains ":"
    if "name" in identifiers and ":" in identifiers["name"]:
      value = self.__create_with_parents(
        field.related_model(),
        identifiers["name"],
        user=self.request.user if self.request.user and self.request.user.is_authenticated else None
      )
    else:
      # Fall back to normal resolver
      value = self.__resolve_related_object(field, identifiers)

    if value is None:
      raise ValueError(
        _("no value supplied for field '{}'").format(field).capitalize()
      )

    # Toggle the relation
    try:
      relation = getattr(self.obj.obj, field.field_name)
      if value in relation.all():
        relation.remove(value)
        self.obj.obj.save()
        self.messages.add(
          _("successfully removed '{}' from field '{}'").format(value, field.name).capitalize(),
          "success"
        )
      else:
        relation.add(value)
        self.obj.obj.save()
        self.messages.add(
          _("successfully added '{}' to field '{}'").format(value, field.name).capitalize(),
          "success"
        )

      return getattr(self.obj, field.field_name)

    except Exception as e:
      traceback.print_exc()
      staff_message = ': ' + str(e) if self.request.user.is_staff else ""
      self.messages.add(
        _("field '{}' in {} '{}' could not be updated to '{}'{}")
          .format(field.name, self.model.name, self.obj, value, staff_message).capitalize(),
        "error"
      )
      return False




  
  def __update_simple_field(self, field):
    """
    Update a simple (non-relational) field on the current object.

    This function retrieves the new value for the given field from the
    request using `__get_value` and applies it via `__update_field`.

    Args:
      field (models.Field): The Django model field to update. This should
                            be a scalar field such as CharField, IntegerField,
                            DateTimeField, etc.

    Returns:
      object: The result of calling `__update_field`, usually the updated
              field value or the updated object depending on implementation.

    Raises:
      ValueError: If no value is supplied and `allow_none` is False.
    """

    # Fetch the new value for the field (None not allowed here)
    value = self.__get_value(field, allow_none=False)

    old_value = getattr(self.obj.obj, field.field_name, None)

    # Update the object field with the resolved value
    return self.__update_field(field, value, old_value=old_value)

    
  def __update_bool(self, field):
    """
    Update a BooleanField on the current object.

    This function supports two modes:
    - If no value is supplied in the request, it toggles the current value
      of the field (True → False, False → True).
    - If a value is supplied, it is converted into a boolean based on
      common truthy/falsey string representations.

    Args:
      field (models.BooleanField): The BooleanField to update.

    Returns:
      object: The result of calling `__update_field`, usually the updated
              field value or the updated object depending on implementation.

    Raises:
      ValueError: If the supplied value cannot be interpreted as boolean.
    """

    # Get the new value from the request; None allowed to support toggling
    value = self.__get_value(field, allow_none=True)

    if value is None:
      # If no value is supplied, toggle the current boolean value
      value = not getattr(self.obj.obj, field.field_name)
    else:
      # Normalize and interpret string/number input into a boolean
      if str(value).lower() in ['1', 'true', 'yes', 'on']:
        value = True
      elif str(value).lower() in ['0', 'false', 'no', 'off']:
        value = False
      else:
        raise ValueError(
          _("invalid boolean value '{}' supplied for field '{}'".format(value, field)).capitalize()
        )

    # Apply the updated boolean value to the field
    return self.__update_field(field, value)

    
  
  
  
  