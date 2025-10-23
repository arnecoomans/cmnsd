from django.db.models import Q, QuerySet, Model
from django.db.models.fields import CharField, TextField
# from django.db import models
from django.db.models.fields.related import ManyToManyField
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models.constants import LOOKUP_SEP

import logging
from typing import Iterable
import traceback

from .utils__request import RequestMixin
from .utils__messages import MessageMixin

class FilterMixin:
  def filter(self, queryset, suppress_search=False, allow_staff=False):
    model = queryset.model
    search_query_char = getattr(settings, 'SEARCH_QUERY_CHARACTER', 'q')
    search_exclude_char = getattr(settings, 'SEARCH_EXCLUDE_CHARACTER', 'exclude')
    search_fields = self.__get_search_fields(model)

    # if len(search_fields) > 0 and self._get_value_from_request(search_query_char, default=False, silent=True) and self._get_value_from_request(search_exclude_char, default=False, silent=True):
    #   # Only apply search filters if there are searchable fields or a search query is provided
    #   suppress_search = True
    
    try:
      ''' Apply model specific access restrictions '''
      queryset = self.__filter_by_restrict_access(queryset)
      ''' Conditionally filter queryset based on field availablity '''
      if 'status' in [field.name for field in model._meta.get_fields()]:
        queryset = self.filter_status(queryset, allow_staff=allow_staff)
      if 'visibility' in [field.name for field in model._meta.get_fields()]:
        queryset = self.filter_visibility(queryset, allow_staff=allow_staff)
      ''' Check if search should be applied or suppressed '''
      if not suppress_search:
        ''' Field specific filtering '''
        if len(search_fields) > 0:
          queryset = self.search_results(queryset, search_fields)
        ''' Free text search '''
        if self._get_value_from_request(search_query_char, default=False, silent=True):
          queryset = self.filter_freetextsearch(queryset)
        ''' Exclude results based on settings '''
        if self._get_value_from_request(search_exclude_char, default=False, silent=True):
          queryset = self.exclude_results(queryset)
    except Exception as e:
      traceback.print_exc()
      staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
      self._add_message(_("an error occurred while filtering{}").capitalize().format(staff_message), 'error')
      self.status = 400
      return QuerySet(model=model).none()
    ''' Return filtered queryset '''
    return queryset.distinct()
  
  ''' Security Measure '''
  def __field_is_secure(self, field_name):
    blocked_fields = ['password'] + getattr(settings, 'SEARCH_BLOCKED_FIELDS', [])
    if field_name in blocked_fields:
        self._add_message(_("field '{}' is not allowed for searching due to security reasons.").format(field_name).capitalize(), "error")
        return False
    if field_name.startswith('_'):
        self._add_message(_("field '{}' is not allowed for searching due to security reasons.").format(field_name).capitalize(), "error")
        return False
    return True
  
  ''' Restrict Access to objects based on model RESTRICT_READ_ACCESS attribute '''
  def __filter_by_restrict_access(self, queryset):
    model = queryset.model
    if hasattr(model, 'RESTRICT_READ_ACCESS'):
      if model.RESTRICT_READ_ACCESS == 'user':
        if self.request.user.is_authenticated:
          queryset = queryset.filter(user=self.request.user)
        else:
          self._add_message(_("you must be logged in to view these items").capitalize(), 'error')
          self.status = 403
          return QuerySet(model=model).none()
    return queryset.distinct()
  
  ''' Get Searchable Fields from request kwargs 
      Loop through request GET and POST parameters and check if they are fields in the model.
      If they are a field, add them to the list of search fields.
  '''
  def __get_search_fields(self, model):
    request_fields = self.__get_searched_fields_from_request()
    model_fields = [field.name for field in model._meta.get_fields()]
    query_fields = []
    for field in request_fields:
      field = field.replace('.', '__')
      if field.split('__')[0] in model_fields:
        query_fields.append(field)
    return query_fields
  
  """ Get all fields from request GET and POST parameters 
      Return a list of all fields in the request GET and POST parameters."""
  def __get_searched_fields_from_request(self):
    search_fields = []
    for key in self.request.GET.keys():
      if key:
        search_fields.append(key)
    for key in self.request.POST.keys():
      if key:
        search_fields.append(key)
    for field in ['csrfmiddlewaretoken']:
      if field in search_fields:
        search_fields.remove(field)
    for field in search_fields:
      if self._get_value_from_request(field, silent=True) in [None, '']:
        search_fields.remove(field)
    return search_fields
  
  ''' Filter by object status '''
  def filter_status(self, queryset, allow_staff=False):
    if allow_staff or getattr(self.request, "user", None) or self.request.user.is_staff:
      return queryset.distinct()
    return queryset.filter(status='p').distinct()
  
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

    if not user or not user.is_authenticated:
      return queryset.filter(visibility="p").distinct()

    # Base visibility: public, community, private(owner)
    filters = (
      Q(visibility="p") |
      Q(visibility="c") |
      Q(visibility="q", user=user)
    )

    # Family visibility (f)
    user_family = None
    try:
      profile = getattr(user, "profile", None)
      if profile:
        family_attr = getattr(profile, "family", None)

        # Case 1: family is a ManyToManyField
        if hasattr(family_attr, "all") and callable(family_attr.all):
          family_ids = list(family_attr.all().values_list("id", flat=True))
          if family_ids:
            filters |= Q(visibility="f", user__profile__family__in=family_ids)

        # Case 2: family is a ForeignKey
        else:
          user_family = family_attr
          if user_family:
            filters |= Q(visibility="f", user__profile__family=user_family)

    except Exception:
      pass  # safely ignore if profile/family unavailable

    # Also allow user’s own family posts (fallback)
    filters |= Q(visibility="f", user=user)

    return queryset.filter(filters)
  
  ''' Free text search filter '''
  def filter_freetextsearch(self, queryset, query=None):
    """ Returns the queryset filtered by a free text search query.
        The query is taken from the request, using the key defined in settings.
        If the query is found, it searches for the query in all CharField and TextField fields of the model.
        If the model has ManyToMany fields, it will also search in the related CharField and TextField fields.
        If no query is found, it returns the original queryset
    """
    if not query:
      query = self._get_value_from_request(getattr(settings, 'SEARCH_QUERY_CHARACTER', 'q'), default=False, silent=True)
    if query:
      # Build a Q object for the search query using the provided query string
      q_obj = self.__build_search_query(query, queryset.model)
      # Apply the Q object filter to the queryset
      queryset = queryset.filter(q_obj).distinct()
    # Return the queryset, which is either filtered or the original queryset
    return queryset.distinct()

  def __get_searchable_fields(self, model):
    """
    Returns a list of fields that can be used for searching in the given model.
    Includes:
    - CharField and TextField fields
    - ManyToMany related CharField/TextField fields
    - If the model has a 'parent' relation, also include the parent model's
      CharField/TextField fields, prefixed with 'parent__'
    """
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

  def __build_q_for_term_group(self, terms, model):
    """ Builds a Q object for a group of terms, where each term must match
        all searchable fields of the model.
        If no terms are provided, it returns an empty Q object.
    """
    fields = self.__get_searchable_fields(model)
    group_q = Q()
    found = False
    for field in fields:
      field_q = Q()
      for term in terms:
        field_q &= Q(**{f"{field}__icontains": term})
      # Check if the AND query has results, else an empty Q object should be returned
      if model.objects.filter(field_q).exists():
        group_q |= field_q
        found = True
    return group_q if found else Q(pk__in=[])
  
  def __build_search_query(self, query_string, model):
    """ Builds a Q object for a free text search query.
        The query string can contain terms separated by '&&' (AND) and '||' (OR).
        If no query string is provided, it returns an empty Q object.
    """
    if not query_string:
      return Q()
    # Replace custom operators with Django's Q operators, to allow __and__ and __or__ in the query string
    # while also allowing for '&&' (encoded to %26%26) and '||' as logical operators
    query_string = query_string.lower().replace('__and__', '&&').replace('__or__', '||')
    query_string = query_string.lower().replace(' and ', '&&').replace(' or ', '||')
    q_obj = Q()
    or_groups = [group.strip() for group in query_string.split('||') if group.strip()]
    found_valid_group = False
    for group in or_groups:
      and_terms = [term.strip() for term in group.split('&&') if term.strip()]
      group_q = self.__build_q_for_term_group(and_terms, model)
      test_qs = model.objects.filter(group_q)
      if test_qs.exists():
        q_obj |= group_q
        found_valid_group = True
    return q_obj if found_valid_group else Q(pk__in=[])
  

  def search_results(self, queryset: QuerySet, search_fields: Iterable[str]) -> QuerySet:
    """Search the queryset dynamically based on request parameters and field paths.

    Args:
      queryset: The base queryset to filter.
      search_fields: Iterable of field lookups (e.g. ['name', 'country__slug']).

    Returns:
      Filtered queryset with all matching results combined via AND logic.
    """
    for field in search_fields:
      value = self._get_value_from_request(field, default=None, silent=True)
      if not value and '__' in field:
        value = self._get_value_from_request(field.replace('__', '.'), default=None, silent=True)
      if value:
        queryset = self.__search_queryset(queryset.model, queryset, field, value)
    return queryset.distinct()


  def __search_queryset(self, model, queryset, field_name, value):
    """Internal helper that filters queryset for a single field path and value."""
    from django.conf import settings
    from django.core.exceptions import FieldDoesNotExist

    # Secure field check
    last_field_name = field_name.split("__")[-1]
    if not self.__field_is_secure(last_field_name):
      return queryset.none()

    # Resolve base related model in chain
    base_field = model
    try:
      for part in field_name.split("__")[:-1]:
        f = base_field._meta.get_field(part)
        base_field = getattr(f, "related_model", None)
        if not base_field:
          return queryset.none()
    except (FieldDoesNotExist, AttributeError):
      return queryset.none()

    try:
      field = base_field._meta.get_field(last_field_name)
    except FieldDoesNotExist:
      return queryset.none()

    # Pick lookup
    lookup_type = "icontains" if field.get_lookup("icontains") else "exact"
    lookup = f"{field_name}__{lookup_type}"
    filters = Q()

    # Split comma-separated values into OR conditions
    for v in [x.strip() for x in str(value).split(",") if x.strip()]:
      filters |= Q(**{lookup: v})

    # Include parent lookup if applicable
    try:
      if any(f.name.lower() == "parent" for f in base_field._meta.get_fields()):
        # Extract prefix (e.g., "descriptions__" from "descriptions__name")
        parts = field_name.split("__")
        prefix = "__".join(parts[:-1])
        if prefix:
          parent_lookup = f"{prefix}__parent__{last_field_name}__{lookup_type}"
        else:
          parent_lookup = f"parent__{last_field_name}__{lookup_type}"

        for v in [x.strip() for x in str(value).split(",") if x.strip()]:
          filters |= Q(**{parent_lookup: v})

    except Exception as e:
      traceback.print_exc()
      staff_message = (
        ": " + str(e)
        if getattr(settings, "DEBUG", False) or getattr(self.request, "user", None) and self.request.user.is_superuser
        else ""
      )
      self._add_message(
        _("an error occurred while searching{}").capitalize().format(staff_message),
        "error",
      )

    return queryset.filter(filters)

  def exclude_results(self, queryset, exclude_character=None, **kwargs):
    """Exclude queryset entries dynamically via ?exclude=field:value.

    Supports multiple ?exclude= params and comma/semicolon separated lists.

    Examples:
      ?exclude=status:archived
      ?exclude=status:archived,is_active:false
      ?exclude=location__slug:huttopia-camping-divonne
      ?exclude=foo:bar&exclude=baz:qux,active:false
    """
    logger = logging.getLogger(__name__)

    exclude_character = exclude_character or getattr(settings, "SEARCH_EXCLUDE_CHARACTER", "exclude")

    # Gather all values from multiple ?exclude=... occurrences
    raw_values = self.request.GET.getlist(exclude_character)
    if not raw_values:
      return queryset.distinct()

    # Merge all exclude strings and allow both comma and semicolon separators
    combined = ",".join(raw_values).replace(";", ",")
    exclude_fields = [f.strip() for f in combined.split(",") if f.strip()]
    for exclusion in exclude_fields:
      # Split only on the first colon
      if ":" in exclusion:
        key, value = exclusion.split(":", 1)
      else:
        key, value = exclusion, "true"

      key, value = key.strip(), value.strip()
      if not key:
        continue

      # Convert common boolean strings
      val_lower = value.lower()
      if val_lower in {"true", "1", "yes", "on"}:
        value = True
      elif val_lower in {"false", "0", "no", "off"}:
        value = False

      # Validate field structure
      try:
        base_field = key.split(LOOKUP_SEP)[0]
        if not hasattr(queryset.model, base_field):
          logger.debug(f"exclude_results: unknown field '{key}' on {queryset.model.__name__}")
          continue
      except Exception as ex:
        logger.warning(f"exclude_results: invalid exclude key '{key}': {ex}")
        continue

      # Apply exclusion safely
      try:
        queryset = queryset.exclude(**{key: value})
      except Exception as ex:
        # Fallback: attempt __icontains if possible
        try:
          queryset = queryset.exclude(**{f"{key}__icontains": value})
        except Exception as inner_ex:
          logger.debug(f"exclude_results: skipping invalid exclusion '{key}:{value}' ({inner_ex})")
          continue

    return queryset.distinct()
  
  def _add_message(self, message = '', level='info'):
    if not hasattr(self, 'messages'):
      if getattr(settings, 'DEBUG', False):
        print("Messages object not found in FilterMixin when trying to add message: {}".format(message))
      return
    self.messages.add(message, level)
  def _get_value_from_request(self, key, default=None, sources=None, silent=False):
    if not hasattr(self, 'get_value_from_request'):
      if getattr(settings, 'DEBUG', False):
        print("get_value_from_request method not found in FilterMixin when trying to get key: {}".format(key))
      return default
    return self.get_value_from_request(key, default=default, sources=sources, silent=silent)