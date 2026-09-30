from django.conf import settings
from django.core.checks import register, Error, Warning
from django.core.exceptions import FieldDoesNotExist

from cmnsd.api.registry import API_REGISTRY


@register()
def check_api_lookup_fields(app_configs, **kwargs):
  """Fail at check-time, not request-time: every @api_model-registered model needs token or slug."""
  errors = []
  for model_cls in API_REGISTRY:
    if not (hasattr(model_cls, 'token') or hasattr(model_cls, 'slug')):
      errors.append(Error(
        f"{model_cls.__name__} is registered via @api_model but has neither "
        "'token' nor 'slug' - API lookups require an ID plus one of these.",
        id="cmnsd.api.E001",
      ))
  return errors


@register()
def check_api_field_relations(app_configs, **kwargs):
  """Fail at check-time, not request-time: @api_field on a relation (FK/
  O2O/M2M) doesn't resolve to a usable value - the dispatcher's raw-value
  fallback (cmnsd/views/api/object_fields.py, _raw_value) only makes
  sense for a plain value or a real method like
  Person.get_relation_to_user; a related manager has no correct "plain
  value" to fall back to and crashes at request time instead (confirmed:
  a ManyRelatedManager is callable() for unrelated Django-internal
  reasons, so the dispatcher's callable-check tries to call it with a
  request= kwarg it doesn't accept).

  _meta.get_fields(), not _meta.fields like api_model()'s own scan -
  _meta.fields excludes relations entirely (so a mis-decorated relation
  wouldn't even be caught by scanning what api_model() found), and
  get_fields() needs the full app registry loaded to compute reverse
  relations, which isn't safe at class-definition/import time (that's
  exactly why api_model() itself is restricted to _meta.fields - see its
  own comment). Checks run after every app has finished loading, so this
  is the first point where scanning the *complete* relation graph is
  actually safe."""
  warnings = []
  for model_cls in API_REGISTRY:
    for field in model_cls._meta.get_fields():
      if not hasattr(field, '_api_field') or not getattr(field, 'is_relation', False):
        continue
      hint = None
      if settings.DEBUG:
        hint = (
          f"Write a proxy method instead (e.g. get_{field.name}"
          "(self, request=None)) that applies filtering, decorate that, "
          "and add a <model>/functions/<method>.html template to render "
          "it (or return a plain value) - see Person.get_tags for the "
          "existing pattern."
        )
      warnings.append(Warning(
        f"{model_cls.__name__}.{field.name} is a relation exposed directly "
        "via @api_field - this has no usable plain value and will raise "
        "at request time.",
        hint=hint,
        obj=model_cls,
        id="cmnsd.api.W001",
      ))
  return warnings


@register()
def check_api_search_fields(app_configs, **kwargs):
  """Fail at check-time, not request-time: every name in
  @api_model(search_fields=[...]) must be a stored CharField/TextField on
  the model - the list endpoint's free-text search runs icontains on
  each (cmnsd/api/filtering.py), which would crash on a typo or a
  relation."""
  errors = []
  for model_cls, entry in API_REGISTRY.items():
    for name in entry.get('search_fields', []):
      try:
        field = model_cls._meta.get_field(name)
      except FieldDoesNotExist:
        field = None
      if field is None or field.get_internal_type() not in ('CharField', 'TextField'):
        errors.append(Error(
          f"{model_cls.__name__}: search_fields entry '{name}' is not a stored "
          "CharField/TextField on this model.",
          id="cmnsd.api.E002",
        ))
  return errors
