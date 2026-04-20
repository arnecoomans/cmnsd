"""
Reusable filtering system for cmnsd-based Django projects.

This version is properly designed for multiple inheritance with Django CBVs.

Mixins:
  - FilterBaseMixin: Shared helpers for messages and request value fetching.
  - FilterAccessMixin: Restrict access based on ownership or model flags.
  - FilterStatusVisibilityMixin: Handle publication/visibility filters.
  - FilterSearchMixin: Handle field-based, free-text, and exclusion search.
  - FilterMixin: Unified façade that keeps the same `.filter()` interface.
"""

from django.db.models import Q, QuerySet
from django.db.models.fields import CharField, TextField, BooleanField
from django.db.models.fields.related import ManyToManyField
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import FieldDoesNotExist
from django.conf import settings
from django.db.models.constants import LOOKUP_SEP
import logging
import traceback
from typing import Iterable


# ---------------------------------------------------------------------------
# BASE MIXIN — common helpers for all filters
# ---------------------------------------------------------------------------

class FilterBaseMixin:
  """Provides compatibility helpers for messaging and request parsing."""

  def _add_message(self, message='', level='info'):
    """Safely add a message if the messages system is available."""
    if hasattr(self, 'messages') and hasattr(self.messages, 'add'):
      self.messages.add(message, level)
    elif getattr(settings, 'DEBUG', False):
      print(f"[{level.upper()}] {message}")

  def _get_value_from_request(self, key, default=None, sources=None, silent=False, request=None):
    """Fetch a value from request or fallback safely if RequestMixin is missing."""
    # Try using RequestMixin if available
    if hasattr(self, 'get_value_from_request'):
      return self.get_value_from_request(key, default=default, sources=sources, silent=silent, request=request)
    
    # Fallback: direct request access
    request = request or getattr(self, 'request', None)
    if not request:
      return default
    
    # Simple GET/POST lookup
    return request.GET.get(key) or request.POST.get(key) or default


# ---------------------------------------------------------------------------
# ACCESS MIXIN — ownership and permission filters
# ---------------------------------------------------------------------------

class FilterAccessMixin(FilterBaseMixin):
  """Provides user-based access restrictions."""

  def _filter_by_restrict_access(self, queryset):
    """Restrict access to objects if the model defines RESTRICT_READ_ACCESS."""
    model = queryset.model
    if not hasattr(model, "RESTRICT_READ_ACCESS"):
      return queryset.distinct()
    
    if model.RESTRICT_READ_ACCESS == "user":
      request = getattr(self, 'request', None)
      user = getattr(request, "user", None) if request else None
      
      if user and user.is_authenticated:
        queryset = queryset.filter(user=user)
      else:
        self._add_message(_("You must be logged in to view these items").capitalize(), "error")
        if hasattr(self, 'status'):
          self.status = 403
        return queryset.none()
    
    return queryset.distinct()


# ---------------------------------------------------------------------------
# STATUS & VISIBILITY MIXIN — publication logic
# ---------------------------------------------------------------------------

class FilterStatusVisibilityMixin(FilterBaseMixin):
  """Provides status and visibility filtering."""

  def filter_status(self, queryset, request=None):
    """Filter queryset by publication status.
    Delegates to the model's filter_status() classmethod when available.
    """
    request = request or getattr(self, 'request', None)
    user = getattr(request, 'user', None) if request else None

    model = queryset.model
    if hasattr(model, 'filter_status'):
      return model.filter_status(queryset, request=request)

    if "status" in [f.name for f in model._meta.get_fields()]:
      return queryset.filter(status="p").distinct()

    return queryset.distinct()

  def filter_visibility(self, queryset, request=None):
    """Filter objects based on the current user's visibility level.
    Delegates to the model's filter_visibility() classmethod when available.
    """
    model = queryset.model
    if "visibility" not in [f.name for f in model._meta.get_fields()]:
      # Model has no field visibility.
      return queryset.distinct()
    
    request = request or getattr(self, 'request', None)

    if hasattr(model, 'filter_visibility'):
      return model.filter_visibility(queryset, request=request)
    # Fallback to default visibility filtering: only show public items (visibility="p")
    if getattr(settings, "DEBUG", False):
      print(f"Filter_visibility called on model { str(model) }, but model has no classmethod filter_visibility. Falling back to public visibility.")
    return queryset.filter(visibility="p").distinct()

  def filter_visibility_fallback(self, queryset, request=None):
    pass

# ---------------------------------------------------------------------------
# SEARCH MIXIN — field, free text, and exclusion search
# ---------------------------------------------------------------------------

class FilterSearchMixin(FilterBaseMixin):
  """Provides search and exclusion filtering."""

  # --- Core field security --------------------------------------------------

  def __field_is_secure(self, field_name):
    blocked = ["password"] + getattr(settings, "SEARCH_BLOCKED_FIELDS", [])
    if field_name in blocked or field_name.startswith("_"):
      self._add_message(
        _("Field '{}' is not allowed for searching due to security reasons.")
          .format(field_name).capitalize(), "error"
      )
      return False
    return True

  # --- Search entrypoint ----------------------------------------------------

  def search(self, queryset, suppress_search=False, mapping={}):
    """Main search entry point."""
    model = queryset.model
    # If search is supressed, do not apply search filters, just return distinct queryset
    if suppress_search:
      return queryset.distinct()
    try:
      # Find searchable fields based on request and model definition
      search_fields = self._get_search_fields(model, mapping=mapping)
      q_char = getattr(settings, "SEARCH_QUERY_CHARACTER", "q")
      exclude_char = getattr(settings, "SEARCH_EXCLUDE_CHARACTER", "exclude")
      if search_fields:
        queryset = self.search_results(queryset, search_fields, mapping=mapping)
        self._store_search_data_for_context(keys=search_fields, mapping=mapping)
      if self._get_value_from_request(q_char, default=False, silent=True):
        queryset = self.filter_freetextsearch(queryset)
        self._store_search_data_for_context(key=q_char)
      if self._get_value_from_request(exclude_char, default=False, silent=True):
        queryset = self.exclude_results(queryset)
        self._store_search_data_for_context(key=exclude_char)
      
    except Exception as e:
      if getattr(settings, 'DEBUG', False):
        traceback.print_exc()
      staff_msg = f": {e}" if getattr(settings, "DEBUG", False) else ""
      self._add_message(_("An error occurred while searching{}").capitalize().format(staff_msg), "error")
      if hasattr(self, 'status'):
        self.status = 400
      return queryset.none()

    return queryset.distinct()

  # -- Build Active Filters for Context ------------------------------------------------
  def _store_search_data_for_context(self, key=None, value=None, keys=None, mapping={}):
    ''' For a given search key and possibly value, store the search query in a dict.
        This dict can then be used in the template to show active filters and their values.
        by calling
        context['active_filters'] = self.get_search_data_for_context()
    '''
    if not hasattr(self, '_search_data_for_context'):
      self._search_data_for_context = {}
    if keys:
      for k in keys:
        if k in mapping.values():
          # Key is a mapped field, find the original request key to fetch the value from request
          for mk, mv in mapping.items():
            if k == mv:
              k = mk
              break
        # Try fetching the value from request for this key
        v = self._get_value_from_request(k, default=None, silent=True)
        if v:
          # Store the value in context under the original key (not the mapped field name)
          self._search_data_for_context[k] = v
    elif key and value is not None:
      self._search_data_for_context[key] = value
    elif key:
      v = self._get_value_from_request(key, default=None, silent=True)
      if v:
        self._search_data_for_context[key] = v
    return self._search_data_for_context
  
  def get_search_data_for_context(self):
    return getattr(self, '_search_data_for_context', {})
  

  # --- Get searchable fields ------------------------------------------------
  def _get_search_fields(self, model, mapping={}):
    if not hasattr(self, '_get_search_fields_cache'):
      request_fields = self._get_searched_fields_from_request()
      # Always start with all concrete fields (includes inherited fields from abstract bases)
      if hasattr(model, "get_model_fields"):
        model_fields = list(model.get_model_fields())
      else:
        model_fields = [f.name for f in model._meta.get_fields()]
      # Layer get_searchable_fields() on top (adds @searchable_function names and custom entries)
      if hasattr(model, "get_searchable_fields"):
        for f in model.get_searchable_fields():
          if f not in model_fields:
            model_fields.append(f)
      model_fields = [f.replace(".", "__") for f in request_fields if f.split("__")[0] in model_fields and f not in mapping]
      # Add mapped fields from request if they exist in the model
      for key, value in mapping.items():
        if key in request_fields:
          if value not in model_fields:
            model_fields.append(value)
      self._get_search_fields_cache = model_fields
    return self._get_search_fields_cache
  
  def _get_searched_fields_from_request(self):
    fields = []
    request = getattr(self, "request", None)
    if not request:
      return []
    for key in list(request.GET.keys()) + list(request.POST.keys()):
      if key not in ["csrfmiddlewaretoken"] and self._get_value_from_request(key, silent=True) not in [None, ""]:
        fields.append(key)
    return fields

  # --- Determine searchable field types ------------------------------------

  def __get_searchable_fields(self, model):
    """Return a list of all CharField/TextField paths usable for free-text search."""
    fields = []
    for field in model._meta.get_fields():
      if isinstance(field, (CharField, TextField)):
        if self.__field_is_secure(field.name):
          fields.append(field.name)
      elif isinstance(field, ManyToManyField):
        related_model = field.remote_field.model
        for related_field in related_model._meta.fields:
          if isinstance(related_field, (CharField, TextField)):
            if self.__field_is_secure(related_field.name):
              fields.append(f"{field.name}__{related_field.name}")
      elif field.name == "parent" and field.is_relation:
        parent_model = field.related_model
        for parent_field in parent_model._meta.fields:
          if isinstance(parent_field, (CharField, TextField)):
            if self.__field_is_secure(parent_field.name):
              fields.append(f"parent__{parent_field.name}")
    return fields

  # --- Free-text search ----------------------------------------------------

  def filter_freetextsearch(self, queryset, query=None):
    """Return queryset filtered by a free-text query using && and || syntax."""
    if not query:
      query = self._get_value_from_request(getattr(settings, "SEARCH_QUERY_CHARACTER", "q"), default=False, silent=True)
    if not query:
      return queryset
    q_obj = self.__build_search_query(query, queryset.model)
    return queryset.filter(q_obj).distinct()

  def __build_q_for_term_group(self, terms, model):
    """Build a Q object for a group of terms, all matching any searchable field."""
    fields = self.__get_searchable_fields(model)
    group_q = Q()
    found = False
    for field in fields:
      field_q = Q()
      for term in terms:
        field_q &= Q(**{f"{field}__icontains": term})
      if model.objects.filter(field_q).exists():
        group_q |= field_q
        found = True
    return group_q if found else Q(pk__in=[])

  def __build_search_query(self, query_string, model):
    """Build a Q object for a free text search query.

    Supports:
      - ?q=foo&&bar (AND)
      - ?q=foo||bar (OR)
      - ?q=foo&&bar||baz (grouped)
    """
    if not query_string:
      return Q()

    query_string = (
      query_string.lower()
      .replace('__and__', '&&')
      .replace('__or__', '||')
      .replace(' and ', '&&')
      .replace(' or ', '||')
    )

    q_obj = Q()
    or_groups = [group.strip() for group in query_string.split('||') if group.strip()]
    found_valid_group = False

    for group in or_groups:
      and_terms = [term.strip() for term in group.split('&&') if term.strip()]
      group_q = self.__build_q_for_term_group(and_terms, model)
      if model.objects.filter(group_q).exists():
        q_obj |= group_q
        found_valid_group = True

    return q_obj if found_valid_group else Q(pk__in=[])

  # --- Exclusion filtering -------------------------------------------------

  def exclude_results(self, queryset, exclude_character=None, **kwargs):
    logger = logging.getLogger(__name__)
    request = getattr(self, 'request', None)
    if not request:
      return queryset
      
    exclude_character = exclude_character or getattr(settings, "SEARCH_EXCLUDE_CHARACTER", "exclude")
    raw_values = request.GET.getlist(exclude_character)
    if not raw_values:
      return queryset

    combined = ",".join(raw_values).replace(";", ",")
    exclude_fields = [f.strip() for f in combined.split(",") if f.strip()]
    for exclusion in exclude_fields:
      if ":" in exclusion:
        key, value = exclusion.split(":", 1)
      else:
        key, value = exclusion, "true"
      key, value = key.strip(), value.strip()
      if not key:
        continue
      if not self.__field_is_secure(key.split("__")[-1]):
        continue
      try:
        queryset = queryset.exclude(**{key: value})
      except Exception:
        try:
          queryset = queryset.exclude(**{f"{key}__icontains": value})
        except Exception as ex:
          logger.debug(f"exclude_results: invalid {key}:{value} ({ex})")
    return queryset.distinct()

  # --- Field search (structured) -------------------------------------------

  def search_results(self, queryset: QuerySet, search_fields: Iterable[str], mapping={}) -> QuerySet:
    for field in search_fields:
      value = self._get_value_from_request(field, default=None, silent=True)
      if not value and "__" in field:
        if field in mapping.values():
          key = next((k for k, v in mapping.items() if v == field), None)
          value = self._get_value_from_request(key, default=None, silent=True)
        else:
          value = self._get_value_from_request(field.replace("__", "."), default=None, silent=True)
      if value:
        queryset = self.__search_queryset(queryset.model, queryset, field, value)
    return queryset.distinct()

  _RANGE_LOOKUPS = {'lte', 'gte', 'lt', 'gt', 'in', 'isnull'}

  def __search_queryset(self, model, queryset, field_name, value):
    """Internal helper that filters queryset for a single field path and value."""
    last_field_name = field_name.split("__")[-1]
    if not self.__field_is_secure(last_field_name):
      return queryset.none()

    # Range/comparison lookup short-circuit (e.g. coord_lat__gte, price__lte)
    if last_field_name in self._RANGE_LOOKUPS:
      try:
        if last_field_name == 'isnull':
          value = str(value).lower() not in ('false', '0', 'no', '')
        return queryset.filter(**{field_name: value})
      except (ValueError, TypeError):
        return queryset

    # Resolve the base model in the lookup chain
    base_field = model
    try:
      for part in field_name.split("__")[:-1]:
        f = base_field._meta.get_field(part)
        base_field = getattr(f, "related_model", None)
        if not base_field:
          return queryset.none()
    except (FieldDoesNotExist, AttributeError):
      return queryset.none()

    # Try to get the actual field on the resolved model
    try:
      field = base_field._meta.get_field(last_field_name)
      is_field = True
    except FieldDoesNotExist:
      field = None
      is_field = False

    # --- Normal field-based filtering --------------------------------------
    if is_field:
      from django.db.models.fields import BooleanField
      
      # Handle boolean fields specially
      if isinstance(field, BooleanField):
        # Convert string to boolean
        bool_value = value.lower() in ('true', '1', 'yes', 'on')
        filters = Q(**{field_name: bool_value})
      else:
        lookup_type = "icontains" if field.get_lookup("icontains") else "exact"
        lookup = f"{field_name}__{lookup_type}"
        filters = Q()

        for v in [x.strip() for x in str(value).split(",") if x.strip()]:
          filters |= Q(**{lookup: v})

      # --- Include parent lookup if applicable (on the base related model) ---
      try:
        parent_field = base_field._meta.get_field("parent")
        if getattr(parent_field, "is_relation", False):
          if "__" in field_name:
            prefix, _last = field_name.rsplit("__", 1)
            parent_path = f"{prefix}__parent__{last_field_name}"
          else:
            parent_path = f"parent__{last_field_name}"
          parent_lookup = f"{parent_path}__{lookup_type}"

          for v in [x.strip() for x in str(value).split(",") if x.strip()]:
            filters |= Q(**{parent_lookup: v})
      except FieldDoesNotExist:
        pass
      except Exception as e:
        if getattr(settings, 'DEBUG', False):
          traceback.print_exc()
        request = getattr(self, 'request', None)
        user = getattr(request, 'user', None) if request else None
        staff_message = (
          ": " + str(e)
          if getattr(settings, "DEBUG", False) or (user and getattr(user, "is_superuser", False))
          else ""
        )
        self._add_message(
          _("An error occurred while searching{}").capitalize().format(staff_message), "error"
        )

      return queryset.filter(filters)

    # --- Callable or pseudo-field fallback ---------------------------------
    results = []
    try:
      request = getattr(self, 'request', None)
      for obj in queryset:
        # Make request available to @searchable_function methods that rely on self.request
        if request and not hasattr(obj, 'request'):
          obj.request = request
        attr = getattr(obj, last_field_name, None)

        # If it's a @searchable_function method, call it
        if callable(attr) and getattr(attr, "is_searchable", False):
          import inspect
          sig = inspect.signature(attr)
          if "request" in sig.parameters:
            attr = attr(request=request)
          elif not sig.parameters:
            attr = attr()

        # Search within iterable or direct value
        if hasattr(attr, "__iter__") and not isinstance(attr, (str, bytes)):
          if any(str(value).lower() in str(item).lower() for item in attr):
            results.append(obj)
        elif attr is not None and str(value).lower() in str(attr).lower():
          results.append(obj)

      if results:
        queryset = queryset.filter(pk__in=[obj.pk for obj in results])
      else:
        queryset = queryset.none()

    except Exception:
      if getattr(settings, 'DEBUG', False):
        traceback.print_exc()

    return queryset


# ---------------------------------------------------------------------------
# COMBINED FACADE — fully backward compatible
# ---------------------------------------------------------------------------

class FilterMixin(
  FilterAccessMixin,
  FilterStatusVisibilityMixin,
  FilterSearchMixin
):
  """Unified, backward-compatible filtering entry point."""

  def filter(self, queryset, request=None, suppress_search=False, mapping={}):
    """Apply all available filters (access, visibility, status, and search)."""
    request = request or getattr(self, 'request', None)
    if not hasattr(self, 'request') and request:
      self.request = request
    
    # model = queryset.model
    try:
      queryset = self._filter_by_restrict_access(queryset)
      queryset = self.filter_status(queryset, request=request)
      queryset = self.filter_visibility(queryset, request=request)
      if not suppress_search:
        queryset = self.search(queryset, 
                               suppress_search=suppress_search, 
                               mapping=mapping)
    except Exception as e:
      if getattr(settings, 'DEBUG', False):
        traceback.print_exc()
      staff_msg = f": {e}" if getattr(settings, "DEBUG", False) else ""
      self._add_message(_("An error occurred while filtering{}").capitalize().format(staff_msg), "error")
      if hasattr(self, 'status'):
        self.status = 400
      return queryset.none()
    return queryset.distinct()
  
  