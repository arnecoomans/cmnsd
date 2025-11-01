"""
Reusable filtering system for cmnsd-based Django projects.

This version preserves backward compatibility with the legacy FilterMixin,
while refactoring logic into modular mixins that share a common base.

Mixins:
  - FilterBaseMixin: Shared helpers for messages and request value fetching.
  - FilterAccessMixin: Restrict access based on ownership or model flags.
  - FilterStatusVisibilityMixin: Handle publication/visibility filters.
  - FilterSearchMixin: Handle field-based, free-text, and exclusion search.
  - FilterMixin: Unified façade that keeps the same `.filter()` interface.

All indentation: 2 spaces
All docstrings: English
"""

from django.db.models import Q, QuerySet
from django.db.models.fields import CharField, TextField
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
    if not hasattr(self, 'messages'):
      if getattr(settings, 'DEBUG', False):
        print(f"Messages object not found in {self.__class__.__name__} when adding message: {message}")
      return
    self.messages.add(message, level)

  def _get_value_from_request(self, key, default=None, sources=None, silent=False, request=None):
    """Fetch a value from request or fallback safely if RequestMixin is missing."""
    if not hasattr(self, 'get_value_from_request'):
      if getattr(settings, 'DEBUG', False):
        print(f"get_value_from_request not found in {self.__class__.__name__} when fetching key: {key}")
      request = getattr(self, 'request', None) if request is None else request
      if request:
        return request.GET.get(key, default)
      return default
    return self.get_value_from_request(key, default=default, sources=sources, silent=silent, request=request)


# ---------------------------------------------------------------------------
# ACCESS MIXIN — ownership and permission filters
# ---------------------------------------------------------------------------

class FilterAccessMixin(FilterBaseMixin):
  """Provides user-based access restrictions."""

  def _filter_by_restrict_access(self, queryset):
    """Restrict access to objects if the model defines RESTRICT_READ_ACCESS."""
    model = queryset.model
    if hasattr(model, "RESTRICT_READ_ACCESS"):
      if model.RESTRICT_READ_ACCESS == "user":
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
          queryset = queryset.filter(user=user)
        else:
          self._add_message(_("you must be logged in to view these items").capitalize(), "error")
          self.status = 403
          return QuerySet(model=model).none()
    return queryset.distinct()


# ---------------------------------------------------------------------------
# STATUS & VISIBILITY MIXIN — publication logic
# ---------------------------------------------------------------------------

class FilterStatusVisibilityMixin(FilterBaseMixin):
  """Provides status and visibility filtering."""

  def filter_status(self, queryset, allow_staff=False):
    """Filter queryset by publication status."""
    user = getattr(self.request, "user", None)
    if allow_staff and user and user.is_staff:
      return queryset.distinct()
    if "status" in [f.name for f in queryset.model._meta.get_fields()]:
      return queryset.filter(status="p").distinct()
    return queryset.distinct()

  def filter_visibility(self, queryset, allow_staff=False):
    """
    Filter objects based on the current user's visibility level.

    Visibility codes:
      'p' = public
      'c' = community (all authenticated users)
      'f' = family (same-family or owner)
      'q' = private (owner only)
    """
    user = getattr(self.request, "user", None)
    model = queryset.model

    if "visibility" not in [f.name for f in model._meta.get_fields()]:
      return queryset

    if not user or not user.is_authenticated:
      return queryset.filter(visibility="p").distinct()

    filters = Q(visibility="p") | Q(visibility="c") | Q(visibility="q", user=user)

    try:
      profile = getattr(user, "profile", None)
      if profile:
        family_attr = getattr(profile, "family", None)
        # ManyToManyField
        if hasattr(family_attr, "all") and callable(family_attr.all):
          family_ids = list(family_attr.all().values_list("id", flat=True))
          if family_ids:
            filters |= Q(visibility="f", user__profile__family__in=family_ids)
        # ForeignKey
        elif family_attr:
          filters |= Q(visibility="f", user__profile__family=family_attr)
    except Exception:
      pass

    filters |= Q(visibility="f", user=user)
    return queryset.filter(filters).distinct()


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
        _("field '{}' is not allowed for searching due to security reasons.")
          .format(field_name).capitalize(), "error"
      )
      return False
    return True

  # --- Search entrypoint ----------------------------------------------------

  def search(self, queryset, suppress_search=False, allow_staff=False):
    """Main search entry point."""
    model = queryset.model
    if suppress_search:
      return queryset.distinct()

    try:
      search_fields = self.__get_search_fields(model)
      q_char = getattr(settings, "SEARCH_QUERY_CHARACTER", "q")
      exclude_char = getattr(settings, "SEARCH_EXCLUDE_CHARACTER", "exclude")

      if search_fields:
        queryset = self.search_results(queryset, search_fields)
      if self._get_value_from_request(q_char, default=False, silent=True):
        queryset = self.filter_freetextsearch(queryset)
      if self._get_value_from_request(exclude_char, default=False, silent=True):
        queryset = self.exclude_results(queryset)
    except Exception as e:
      traceback.print_exc()
      staff_msg = f": {e}" if getattr(settings, "DEBUG", False) else ""
      self._add_message(_("an error occurred while searching{}").capitalize().format(staff_msg), "error")
      self.status = 400
      return QuerySet(model=model).none()

    return queryset.distinct()

  # --- Get searchable fields ------------------------------------------------

  def __get_search_fields(self, model):
    request_fields = self.__get_searched_fields_from_request()
    if hasattr(model, "get_searchable_fields"):
      model_fields = model.get_searchable_fields()
    elif hasattr(model, "get_model_fields"):
      model_fields = model.get_model_fields()
    else:
      model_fields = [f.name for f in model._meta.get_fields()]
    return [f.replace(".", "__") for f in request_fields if f.split("__")[0] in model_fields]

  def __get_searched_fields_from_request(self):
    fields = []
    req = getattr(self, "request", None)
    if not req:
      return fields
    for key in list(req.GET.keys()) + list(req.POST.keys()):
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
    exclude_character = exclude_character or getattr(settings, "SEARCH_EXCLUDE_CHARACTER", "exclude")
    raw_values = self.request.GET.getlist(exclude_character)
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
      try:
        queryset = queryset.exclude(**{key: value})
      except Exception:
        try:
          queryset = queryset.exclude(**{f"{key}__icontains": value})
        except Exception as ex:
          logger.debug(f"exclude_results: invalid {key}:{value} ({ex})")
    return queryset.distinct()

  # --- Field search (structured) -------------------------------------------

  def search_results(self, queryset: QuerySet, search_fields: Iterable[str]) -> QuerySet:
    for field in search_fields:
      value = self._get_value_from_request(field, default=None, silent=True)
      if not value and "__" in field:
        value = self._get_value_from_request(field.replace("__", "."), default=None, silent=True)
      if value:
        queryset = self.__search_queryset(queryset.model, queryset, field, value)
    return queryset.distinct()

  def __search_queryset(self, model, queryset, field_name, value):
    """Internal helper that filters queryset for a single field path and value.

    Extends default search logic with:
      - Secure field validation.
      - Parent relation lookup (only when valid).
      - Callable and iterable fallbacks.
    """
    last_field_name = field_name.split("__")[-1]
    if not self.__field_is_secure(last_field_name):
      return queryset.none()

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
      lookup_type = "icontains" if field.get_lookup("icontains") else "exact"
      lookup = f"{field_name}__{lookup_type}"
      filters = Q()

      for v in [x.strip() for x in str(value).split(",") if x.strip()]:
        filters |= Q(**{lookup: v})

      # --- Include parent lookup if applicable (on the base related model) ---
      try:
        parent_field = base_field._meta.get_field("parent")
        if getattr(parent_field, "is_relation", False):
          # Insert 'parent' into lookup path correctly
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
        traceback.print_exc()
        staff_message = (
          ": " + str(e)
          if getattr(settings, "DEBUG", False)
          or getattr(getattr(self, "request", None), "user", None) and getattr(self.request.user, "is_superuser", False)
          else ""
        )
        self._add_message(
          _("an error occurred while searching{}").capitalize().format(staff_message), "error"
        )

      return queryset.filter(filters)

    # --- Callable or pseudo-field fallback ---------------------------------
    results = []
    try:
      for obj in queryset:
        attr = getattr(obj, last_field_name, None)

        # If it’s a @searchable_function method, call it
        if callable(attr) and getattr(attr, "is_searchable", False):
          import inspect
          sig = inspect.signature(attr)
          if "request" in sig.parameters:
            attr = attr(request=getattr(self, "request", None))
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

  def filter(self, queryset, request=None, suppress_search=False, allow_staff=False):
    """Apply all available filters (access, visibility, status, and search)."""
    self.request = getattr(self, "request", request)
    model = queryset.model
    try:
      queryset = self._filter_by_restrict_access(queryset)
      queryset = self.filter_status(queryset, allow_staff=allow_staff)
      queryset = self.filter_visibility(queryset, allow_staff=allow_staff)
      if not suppress_search:
        queryset = self.search(queryset, suppress_search, allow_staff)
    except Exception as e:
      traceback.print_exc()
      staff_msg = f": {e}" if getattr(settings, "DEBUG", False) else ""
      self._add_message(_("an error occurred while filtering{}").capitalize().format(staff_msg), "error")
      self.status = 400
      return QuerySet(model=model).none()
    return queryset.distinct()