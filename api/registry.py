'''
  CMNSD Dynamic API Registry
  Lets the API layer access models dynamically, without hardcoded per-model
  API code. Two mechanisms work together:

  - detect_capabilities() duck-types a model's CMNSD capabilities (status,
    visibility), independent of which mixin - if any - provided them.
  - @api_model / @api_field / @api_action explicitly register a model (and
    its exposed fields/actions) as API-accessible.

  API_REGISTRY must only be read after all app models are loaded - build or
  validate consumers of it in AppConfig.ready(), or lazily on first API
  access, never at API-app import time (app load order isn't guaranteed).
'''

API_REGISTRY = {}


def detect_capabilities(model_cls):
  """Duck-type a model's CMNSD capabilities via the methods it exposes."""
  caps = {}
  if hasattr(model_cls, 'is_visible_to') and hasattr(model_cls, 'filter_visibility'):
    caps['visibility'] = 'field-agnostic'
  if hasattr(model_cls, 'filter_status'):
    caps['status'] = 'field-agnostic'
  return caps


def api_model(name=None, *, status=True, visibility=True, search_fields=()):
  """
  Register a model class as accessible via the CMNSD dynamic API.

  search_fields:
    Stored CharField/TextField names the list endpoint's free-text search
    (?<CMNSD_SEARCH_CHARACTER>=...) matches against. Empty = the model
    isn't free-text searchable. Explicit, like @api_field - nothing is
    searchable unless listed here (cmnsd/api/filtering.py, checked by
    check_api_search_fields).

  status / visibility:
    True          (default) = auto-detect via duck-typing, apply CMNSD default logic if found
    False                   = capability may be present but the API should not apply CMNSD's
                               default interpretation of it (e.g. overridden choices)
    'field_name'            = capability lives under a non-standard field/attribute name
  """
  def decorator(model_cls):
    entry = API_REGISTRY.setdefault(model_cls, {
      "name": name or model_cls._meta.model_name,
      "capabilities": {}, "fields": {}, "actions": {},
    })
    entry["search_fields"] = list(search_fields)
    detected = detect_capabilities(model_cls)
    for cap, requested in (('status', status), ('visibility', visibility)):
      if requested is False:
        continue
      if isinstance(requested, str):
        entry["capabilities"][cap] = {"field": requested, "apply_default_logic": False}
      elif cap in detected:
        entry["capabilities"][cap] = {"field": cap, "apply_default_logic": True}

    # dir(), not vars(model_cls) - vars() only sees attributes defined
    # directly in this class's own __dict__, missing anything defined on
    # a mixin (FamilyShorthand, EventShorthand, RelationshipLabel, ...) -
    # which is where most of a model's methods actually live in this
    # project's architecture. dir() walks the full MRO, so a decorated
    # mixin method is found regardless of which file it's defined in.
    for attr_name in dir(model_cls):
      attr = getattr(model_cls, attr_name, None)
      if hasattr(attr, "_api_field"):
        entry["fields"][attr_name] = attr._api_field
      if hasattr(attr, "_api_action"):
        entry["actions"][attr_name] = attr._api_action

    # A stored field decorated in the class body (e.g. `called_name =
    # api_field(readonly=False)(models.CharField(...))`) doesn't survive
    # the dir()/getattr() scan above: Django's metaclass replaces the
    # class attribute with a DeferredAttribute descriptor that doesn't
    # carry over _api_field. The marker DOES survive on the underlying
    # Field instance in _meta, though - confirmed empirically - so stored
    # fields need this separate pass.
    #
    # _meta.fields (forward, concrete fields only), not _meta.get_fields() -
    # get_fields() computes the full cross-app relation tree, which needs
    # every app's models loaded and blows up with AppRegistryNotReady here:
    # @api_model() runs at class-definition time, while this very model is
    # still being imported as part of app loading. _meta.fields only looks
    # at this model's own already-contributed fields, so it's safe at
    # decoration time. Doesn't cover ManyToMany (lives in
    # _meta.many_to_many) - add that pass if/when a M2M needs exposing.
    for field in model_cls._meta.fields:
      if hasattr(field, "_api_field"):
        entry["fields"][field.name] = field._api_field
    return model_cls
  return decorator


def api_field(*, readonly=True):
  """Explicitly expose a model attribute/method through the API. No implicit exposure.

  On a method: use as a normal decorator, @api_field(readonly=True) above
  a def. On a stored field: @-decorator syntax can't apply to a plain
  assignment (a real Python SyntaxError, not a subtle bug - e.g. `kind =
  models.CharField(...)` under an `@api_field(...)` line) - wrap the
  field expression in a call instead: `kind = api_field(readonly=True)
  (models.CharField(...))`, matching Person.called_name/biography.

  Don't decorate a relation (ForeignKey/OneToOneField/ManyToManyField/
  GenericRelation) directly - it has no usable plain value, and
  check_api_field_relations (cmnsd/checks/ApiChecks.py) will warn about
  it at check-time. Write a proxy method instead (e.g.
  get_<field>(self, request=None)) that applies filtering, decorate
  that, and add a <model>/functions/<method>.html template to render it
  (or return a plain value) - see Person.get_tags."""
  def decorator(func):
    func._api_field = {"readonly": readonly}
    return func
  return decorator


def api_action(*, requires_auth=True):
  """Explicitly expose a model method as a callable API action."""
  def decorator(method):
    method._api_action = {"requires_auth": requires_auth}
    return method
  return decorator
