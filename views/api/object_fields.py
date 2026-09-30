import inspect

import minify_html

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import FieldDoesNotExist
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils.html import conditional_escape
from django.views.decorators.http import require_GET

from cmnsd.api.filtering import visible_queryset
from cmnsd.api.registry import API_REGISTRY

# Label for whichever extension a matching template was found under - not
# a fixed list the API is limited to (see _render_field/object_fields),
# just how to name the content-type once a template match is found.
# Unknown extensions still render, they just default to text/plain.
_CONTENT_TYPES = {
  'html': 'text/html',
  'txt': 'text/plain',
  'md': 'text/markdown',
}


def _resolve_model(model_name):
  """API_REGISTRY is keyed by model class, but the URL only has the
  registered name string - reverse-lookup by entry['name']. Small
  registry, linear scan is fine; switch to a name-keyed index only if
  this ever shows up in profiling."""
  for model_cls, entry in API_REGISTRY.items():
    if entry['name'] == model_name:
      return model_cls, entry
  raise Http404(f"'{model_name}' is not an API-registered model.")


def _raw_value(obj, name, request):
  """The field's plain value - a real stored field's value as-is, or a
  decorated method's return value. Matches the old cmnsd
  @ajax_function(request=None) convention every currently-decorated
  method follows."""
  value = getattr(obj, name)
  # inspect.ismethod(), not callable() - a bound method (get_full_name,
  # get_relation_to_user, ...) is both, but so is a related manager
  # (ManyRelatedManager has its own unrelated __call__) with a completely
  # different, incompatible signature. Calling one of those here would
  # raise a TypeError at request time instead of resolving to a value -
  # confirmed empirically. check_api_field_relations (cmnsd/checks/
  # ApiChecks.py) already catches a relation decorated directly, but this
  # is the general-purpose guard: only call something that's actually one
  # of our own @ajax_function(request=None)-style methods.
  if inspect.ismethod(value):
    value = value(request=request)
  # str(), not raw - a value may be a still-lazy gettext_lazy() proxy
  # (e.g. get_relation_to_user()'s format_lazy() result), which
  # JsonResponse's encoder can't serialize on its own. Forcing it here,
  # inside an active request/locale, is the safe place to resolve it -
  # unlike the earlier {% translate %} template gotcha, this isn't
  # evaluating a lazy value before a request context exists.
  return str(value) if value is not None else None


def _template_namespace(model_cls, field_name):
  """'fields' for a real stored model field (a plain CharField/TextField/
  etc, e.g. called_name, biography), 'functions' for anything else (a
  method/property exposed via @api_field, e.g. get_full_name,
  get_relation_to_user) - detected via _meta.get_field(), not guessed
  from the name. Detection over brute-forcing both directories: a name
  is unambiguously one or the other (a model can't have both a field and
  a method of the same name), so there's always exactly one right
  answer, not two paths worth trying."""
  try:
    model_cls._meta.get_field(field_name)
    return 'fields'
  except FieldDoesNotExist:
    return 'functions'


def _find_template(model_cls, model_name, field_name, ext):
  """<model>/fields/<field>.<ext> or <model>/functions/<field>.<ext> (see
  _template_namespace) - the exact convention already in use throughout
  the project for the functions/ half (person/functions/get_full_name.html
  etc, see person_detail.html's {% include %} calls), not a separate
  API-specific naming scheme. Keyed by model name, not app label - an app
  can hold more than one model, and app label alone wouldn't disambiguate
  two same-named fields on different models in the same app (e.g. a
  called_name on both Person and some future Content model, both in an
  app with more than one model). Returns None rather than raising, so
  callers fall back instead of branching on TemplateDoesNotExist
  themselves - "check if it exists, fall back to the model's response
  if it doesn't" (docs/cmnsd_api_design.md #Rendering)."""
  namespace = _template_namespace(model_cls, field_name)
  try:
    return get_template(f'{model_name}/{namespace}/{field_name}.{ext}')
  except TemplateDoesNotExist:
    return None


def _debug_block(entry, obj, names):
  return {'model': entry['name'], 'object': str(obj), 'fields': names}


def _messages_block(request):
  """Placeholder: nothing in this read-only (v1) view queues a message
  itself yet - there's no write path here to say "saved" about. This
  just picks up and serializes whatever django.contrib.messages already
  has queued (e.g. carried over from a prior request in the same
  session), mirroring the {% if messages %} template tag, so the JS
  layer has a real place to look once a write path exists to actually
  push something into it. get_messages() also marks them read/consumed,
  same as rendering them in a template does - a message shows up in
  exactly one response, not every one until the session expires."""
  return [
    {'text': str(m), 'level': m.level_tag, 'tags': m.tags}
    for m in messages.get_messages(request)
  ]


def _render_context(entry, obj, field_name, request, debug_names):
  # Keyed by the model's own registry name (e.g. person=obj), not a
  # generic object=obj - matches what the existing function-templates
  # already expect (get_full_name.html etc read {{ person.* }}, not
  # {{ object.* }}).
  context = {entry['name']: obj, 'field': field_name, 'request': request}
  if settings.DEBUG:
    context['debug'] = _debug_block(entry, obj, debug_names)
  return context


@require_GET
def object_fields(request, model, identifier, field=None):
  """GET api/<model>/<identifier>/ (all exposed fields) or
  GET api/<model>/<identifier>/<field>/ (one, or a comma-separated few) -
  one view for both, per docs/cmnsd_api_design.md ("URL shape"): the
  field-scoped URL is the same lookup + permission check as the
  all-fields one, just narrowed by an optional kwarg, not a different
  operation. Read-only (v1 scope) - see docs/cmnsd_api_design.md #Writing
  for why writes aren't handled here yet.

  <identifier> is the object's token (docs/cmnsd_api_design.md
  #Identification) - except in DEBUG, where an all-digits value is tried
  as a raw pk instead, purely so a token doesn't have to be looked up by
  hand while manually testing in a browser. Never in production, and
  nothing reverses a URL this way - the site's own templates/JS always
  build these URLs from the real token.

  Rendering: each field is packed into the JSON response as a rendered
  HTML fragment if <model>/fields/<field>.html or
  <model>/functions/<field>.html exists (see _template_namespace), else
  as its plain value - see docs/cmnsd_api_design.md #Rendering.
  ?format=<ext> on a single-field request instead returns that field's
  own template raw (not JSON-wrapped) if one exists for that extension;
  otherwise it's ignored and the normal JSON response is returned - no
  fixed set of supported extensions."""
  model_cls, entry = _resolve_model(model)
  lookup = {'pk': identifier} if settings.DEBUG and identifier.isdigit() else {'token': identifier}
  obj = get_object_or_404(visible_queryset(model_cls, entry, request), **lookup)

  unknown = []
  if field:
    requested = [name.strip() for name in field.split(',') if name.strip()]
    unknown = [name for name in requested if name not in entry['fields']]
    names = [name for name in requested if name in entry['fields']]
    if unknown and settings.DEBUG:
      # errors.unknown_fields already carries this in the JSON, but that's
      # easy to miss without opening devtools - in DEBUG, also push it
      # through messages so the JS surfaces it in the UI itself, the same
      # way a template-rendered page would flash an error. Not in
      # production: an end user hitting an unexposed field name isn't
      # something to announce to them, just something to log/ignore.
      messages.error(request, f"[DEBUG] Unknown or unexposed field(s): {', '.join(unknown)}")
    if not names:
      # Every requested name was invalid - nothing to return, so this is
      # the one case that's genuinely an error, not a partial result.
      # Same shape as the 200 case below (model/token/fields present,
      # just empty), not a different one-off error format - a client
      # shouldn't need to branch on status code to parse this.
      return JsonResponse({
        'model': entry['name'], 'token': obj.token, 'fields': {},
        'errors': {'unknown_fields': unknown},
        'messages': _messages_block(request),
      }, status=400)
  else:
    names = list(entry['fields'].keys())

  # An explicit format only makes sense for a single field - there's no
  # sensible way to combine several heterogeneous rendered fragments into
  # one non-JSON response. Falls straight through to the default JSON
  # path below if no matching template exists for that extension.
  requested_format = request.GET.get('format')
  if requested_format and len(names) == 1:
    template = _find_template(model_cls, entry['name'], names[0], requested_format)
    if template:
      context = _render_context(entry, obj, names[0], request, names)
      content_type = _CONTENT_TYPES.get(requested_format, 'text/plain')
      return HttpResponse(template.render(context, request), content_type=content_type)

  # The requested extension governs packing too, not just the single-field
  # raw-bypass above - a multi-field request with ?format=txt should still
  # prefer each field's own .txt template where one exists, not silently
  # fall back to .html as if no format had been requested at all.
  pack_ext = requested_format or 'html'

  fields = {}
  for name in names:
    template = _find_template(model_cls, entry['name'], name, pack_ext)
    if template:
      rendered = template.render(_render_context(entry, obj, name, request, names), request)
      if pack_ext == 'html':
        # Unlike a full page response, cmnsd.middleware.html_output never
        # sees this - it gates on Content-Type: text/html, and this
        # fragment is about to become a JSON string value, not a response
        # of its own. minify_html directly, reusing the same minifier
        # that middleware uses (not BeautifulSoup.prettify() - already
        # confirmed elsewhere, see html_output.py, that it corrupts
        # inline tags like <mark> by inserting a newline around them
        # regardless of DEBUG state; a fragment embedded in JSON has no
        # "readable page source" debugging use either way, so minify
        # unconditionally rather than mirror html_output's DEBUG-gated
        # pass-through). Only for html - minify_html assumes real HTML
        # structure, running it on an arbitrary .txt/.md template's
        # output could corrupt content that was never HTML to begin with.
        rendered = minify_html.minify(rendered, minify_js=True, minify_css=True)
      fields[name] = rendered
    else:
      # No template for the requested extension - falls back to the
      # plain resolved value, not a further fallback to .html. Asking
      # for a specific format and silently getting a different one back
      # would be more confusing than getting the raw value.
      value = _raw_value(obj, name, request)
      # The client inserts html-packed values as-is (cmnsd.js/fields.js),
      # so a raw value - possibly user content - is escaped here. Only
      # for html: a .txt/.md value is never inserted as markup.
      # conditional_escape, not escape: a method returning mark_safe()
      # HTML on purpose is left alone.
      if pack_ext == 'html' and value is not None:
        value = conditional_escape(value)
      fields[name] = value

  response = {
    'model': entry['name'], 'token': obj.token, 'fields': fields,
    'messages': _messages_block(request),
  }
  if unknown:
    # A partial mix, not all-or-nothing: an unknown field name isn't
    # sensitive (it's readable straight out of the templates/JS that call
    # this), so there's no reason to withhold the fields that *did*
    # resolve just because one name in the list was wrong - see
    # docs/cmnsd_api_design.md #Response. Centralized under 'errors' (not
    # a top-level 'unknown_fields') so any future error category has one
    # place to live, not a growing list of one-off top-level keys.
    response['errors'] = {'unknown_fields': unknown}
  if settings.DEBUG:
    response['debug'] = _debug_block(entry, obj, names)
  return JsonResponse(response)
