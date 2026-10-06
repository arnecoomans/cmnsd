from django.core.exceptions import FieldDoesNotExist
from django.db.models import Count
from django.http import Http404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from cmnsd.api.filtering import visible_queryset

from .lookup import resolve_model
from .response import api_response, api_view

LIMIT = 10


@api_view
@require_GET
def object_suggest(request, model, name):
  """GET api/<model>/suggest/<name>/?q=... - suggestions for a free-text
  field whose values recur but aren't a model of their own (a book's
  publisher, a last name): the distinct existing values containing the
  text, most used first, at most 10 - only from objects this viewer may
  see, so a suggestion can't reveal what's hidden (e.g. a hidden person's
  surname). Declared per model: api_suggest_fields = {name: lookup path},
  e.g. {'publisher': 'book_detail__publisher'}; nothing else is served.
  Signed-in only: suggestions are for editing. Response: {values: [...]}.
  Filled into a <datalist> by cmnsd.js suggest.js
  (cmnsd.forms.widgets.SuggestInput)."""
  model_cls, entry = resolve_model(model)
  if not request.user.is_authenticated:
    return api_response(request, status=403, entry=entry, values=[], error=_("Sign in to do this."), errors={'permission': 'sign_in'})
  path = (getattr(model_cls, 'api_suggest_fields', {}) or {}).get(name)
  if path is None:
    raise Http404(f"'{name}' has no suggestions.")
  query = request.GET.get('q', '').strip()
  if not query:
    return api_response(request, entry=entry, values=[])
  rows = (
    visible_queryset(model_cls, entry, request)
    .filter(**{f'{path}__icontains': query})
    .exclude(**{path: ''})
    .values(path).annotate(uses=Count('pk', distinct=True))
    .order_by('-uses', path)[:LIMIT]
  )
  return api_response(request, entry=entry, values=[row[path] for row in rows])
