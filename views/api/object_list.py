import minify_html

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils.html import conditional_escape
from django.views.decorators.http import require_GET

from cmnsd.api.filtering import build_list, list_context

from .object_fields import _messages_block, _resolve_model


@require_GET
def object_list(request, model):
  """GET api/<model>/?<search character>=...&<field>=... - the visible
  objects of a model, narrowed by cmnsd/api/filtering.py (explicit
  allowlist: search_fields for free text, @api_field stored fields for
  exact filters). Read-only, unpaginated (v1) - see
  docs/cmnsd_api_design.md #Listing.

  Rendering follows the field endpoint: <model>/<model>_list.html, if it
  exists, is rendered with the same context an HTML view gets from
  list_context() and packed into the JSON as `html` - so a page that
  server-renders that template and a JS live search that swaps it in
  produce identical markup. Without a template, `results` carries each
  object's token and escaped str()."""
  model_cls, entry = _resolve_model(model)
  result = build_list(model_cls, request)
  objects = list(result['objects'])

  if result['errors'] and settings.DEBUG:
    # Same reasoning as object_fields' unknown_fields message: easy to
    # miss in the JSON without devtools, so surface it in DEBUG only.
    messages.error(request, f"[DEBUG] List filter errors: {result['errors']}")

  response = {'model': entry['name'], 'count': len(objects)}
  try:
    template = get_template(f"{entry['name']}/{entry['name']}_list.html")
  except TemplateDoesNotExist:
    template = None
  if template:
    result['objects'] = objects
    rendered = template.render(list_context(model_cls, result, request), request)
    response['html'] = minify_html.minify(rendered, minify_js=True, minify_css=True)
  else:
    response['results'] = [
      {'token': obj.token, 'name': conditional_escape(str(obj))} for obj in objects
    ]

  response['messages'] = _messages_block(request)
  if result['errors']:
    response['errors'] = result['errors']
  if settings.DEBUG:
    response['debug'] = {'model': entry['name'], 'query': result['query'], 'params': dict(request.GET)}
  return JsonResponse(response)
