import minify_html

from django.conf import settings
from django.contrib import messages

from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils.html import conditional_escape
from django.views.decorators.http import require_GET

from cmnsd.api.filtering import build_list, list_context

from .lookup import resolve_model
from .response import api_response, api_view


@api_view
@require_GET
def object_list(request, model):
  """GET api/<model>/?<search character>=...&<field>=... - the visible
  objects of a model, narrowed by cmnsd/api/filtering.py (explicit
  allowlist: search_fields for free text, @api_field stored fields for
  exact filters). Read-only, unpaginated (v1) - see
  docs/api.md #Listing.

  Rendering follows the field endpoint: <model>/<model>_list.html, if it
  exists, is rendered with the same context an HTML view gets from
  list_context() and packed into the JSON as `html` - so a page that
  server-renders that template and a JS live search that swaps it in
  produce identical markup. Without a template, `results` carries each
  object's token and escaped str().

  ?format=picker: for a picker (cmnsd.js picker.js) - renders
  <model>/<model>_picker.html instead (compact rows to choose from), or
  falls back to `results`. Same filtering and visibility."""
  model_cls, entry = resolve_model(model)
  result = build_list(model_cls, request)
  objects = list(result['objects'])

  if result['errors'] and settings.DEBUG:
    # Same reasoning as object_fields' unknown_fields message: easy to
    # miss in the JSON without devtools, so surface it in DEBUG only.
    messages.error(request, f"[DEBUG] List filter errors: {result['errors']}")

  response = {'count': len(objects)}
  suffix = 'picker' if request.GET.get('format') == 'picker' else 'list'
  if suffix == 'picker' and result['query']:
    objects = rank_by_name(objects, result['query'], request)
  try:
    template = get_template(f"{entry['name']}/{entry['name']}_{suffix}.html")
  except TemplateDoesNotExist:
    template = None
  if template:
    result['objects'] = objects
    rendered = template.render(list_context(model_cls, result, request), request)
    response['html'] = minify_html.minify(rendered, minify_js=True, minify_css=True)
  else:
    response['results'] = [
      {'token': obj.token, 'name': conditional_escape(_display(obj, request))} for obj in objects
    ]

  # Unknown or invalid filters are a partial success: reported under
  # errors, ok stays true.
  return api_response(
    request, entry=entry, errors=result['errors'] or None,
    debug={'model': entry['name'], 'query': result['query'], 'params': dict(request.GET)},
    **response,
  )


def _display(obj, request):
  """An object's name as this viewer may see it: its api_display(request)
  if the model defines one (e.g. an event naming only the people the
  viewer may see), else str()."""
  display = getattr(obj, 'api_display', None)
  return display(request) if display else str(obj)


def rank_by_name(objects, query, request=None):
  """Picker results, best first: a name that starts with the search, then
  one with a word that does ("Eric" finds "Eric Coomans" before "Frank,
  Jan en Eric"), then the rest - each group in the list's own order (a
  stable sort). For format=picker, and for a search page that puts the
  best hits first (fmly's /search/); a list page keeps its order."""
  query = query.casefold()

  def rank(obj):
    name = _display(obj, request).casefold()   # never rank on a hidden name
    if name.startswith(query):
      return 0
    if any(word.startswith(query) for word in name.replace('-', ' ').split()):
      return 1
    return 2

  return sorted(objects, key=rank)
