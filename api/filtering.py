'''
  Queryset narrowing for the CMNSD API - shared by the generic list
  endpoint (cmnsd/views/api/object_list.py) and any HTML view that lists
  the same model (e.g. people's PersonListView), so a page and its API
  always return the same objects for the same query string.

  Explicit allowlist, not "any model field": a filter parameter is only
  honored for a stored field exposed via @api_field, and free-text search
  only covers @api_model(search_fields=[...]). No __ lookups or relation
  traversal - an open filter lets a caller ask yes/no questions about
  data they can't see (e.g. ?related_user__email__startswith=a), even
  though the objects themselves are visibility-filtered.
'''

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.models import Q

from cmnsd.api.registry import API_REGISTRY

# Query parameters with a meaning of their own, never treated as filters.
_RESERVED_PARAMS = {'format'}


def search_character():
  return getattr(settings, 'CMNSD_SEARCH_CHARACTER', 'q')


def visible_queryset(model_cls, entry, request, queryset=None):
  """Status/visibility filtering, applied before anything is returned -
  the single place both the field and list endpoints get this from.
  apply_default_logic gates whether CMNSD's own filter_status()/
  filter_visibility() semantics apply - a capability present with
  apply_default_logic=False means the model opted out of the default
  interpretation, so this leaves it alone rather than guessing a
  replacement."""
  if queryset is None:
    queryset = model_cls.objects.all()
  status_cap = entry['capabilities'].get('status')
  if status_cap and status_cap['apply_default_logic']:
    queryset = model_cls.filter_status(queryset, request)
  visibility_cap = entry['capabilities'].get('visibility')
  if visibility_cap and visibility_cap['apply_default_logic']:
    queryset = model_cls.filter_visibility(queryset, request)
  return queryset


def filterable_fields(model_cls, entry):
  """Stored fields exposed via @api_field - the only names a filter
  parameter may use. Methods exposed via @api_field aren't filterable:
  they have no column to filter on."""
  names = {}
  for name in entry['fields']:
    try:
      names[name] = model_cls._meta.get_field(name)
    except FieldDoesNotExist:
      continue
  return names


def filter_queryset(model_cls, entry, queryset, params):
  """Narrow queryset by params (a QueryDict, e.g. request.GET).

  - ?<search character>=jan bakker: every whitespace-separated term must
    match (icontains) at least one of the model's search_fields.
  - ?<field>=value: exact match on an @api_field-exposed stored field,
    value converted via the field's own to_python(), and checked against
    the field's choices if it has any. An empty value means no filter.

  Returns (queryset, query, errors). Unknown or invalid parameters are
  ignored and reported, not fatal - same partial-success stance as the
  field endpoint's unknown_fields."""
  errors = {}
  q_char = search_character()
  query = params.get(q_char, '').strip()

  if query:
    search_fields = entry.get('search_fields') or []
    if search_fields:
      for term in query.split():
        term_q = Q()
        for field in search_fields:
          term_q |= Q(**{f'{field}__icontains': term})
        queryset = queryset.filter(term_q)
    else:
      errors['search'] = f"'{entry['name']}' is not searchable."

  allowed = filterable_fields(model_cls, entry)
  unknown, invalid = [], []
  for key in params:
    if key in _RESERVED_PARAMS or key == q_char:
      continue
    field = allowed.get(key)
    if field is None:
      unknown.append(key)
      continue
    raw = params.get(key)
    if raw in ('', None):
      continue  # ?field= means "no filter on field" (e.g. an "All" option)
    try:
      value = field.to_python(raw)
    except ValidationError:
      invalid.append(key)
      continue
    if field.choices and value not in {choice for choice, _label in field.flatchoices}:
      invalid.append(key)
      continue
    queryset = queryset.filter(**{key: value})
  if unknown:
    errors['unknown_filters'] = unknown
  if invalid:
    errors['invalid_filters'] = invalid

  return queryset, query, errors


def build_list(model_cls, request, queryset=None, params=None):
  """Visible + filtered objects for a list, ready to render.

  After filtering, a queryset method for_list() is applied if the model
  defines one - the hook for list-specific batching (e.g. Person attaches
  birth/death events in one query instead of one per row). It may return
  a list, so it runs last.

  Returns dict(objects, query, errors)."""
  entry = API_REGISTRY[model_cls]
  qs = visible_queryset(model_cls, entry, request, queryset)
  qs, query, errors = filter_queryset(model_cls, entry, qs, request.GET if params is None else params)
  objects = qs.for_list() if hasattr(qs, 'for_list') else qs
  return {'objects': objects, 'query': query, 'errors': errors}


def list_context(model_cls, result, request):
  """Template context for <model>/<model>_list.html - one shape for the
  HTML view and the API, so the same template renders in both."""
  name = API_REGISTRY[model_cls]['name']
  return {f'{name}_list': result['objects'], 'search_query': result['query'], 'request': request}
