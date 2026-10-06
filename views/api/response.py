"""
One response shape for every cmnsd API endpoint (docs/api.md
#Response), success or error, so a client never has to branch per
endpoint:

  {
    "ok": true | false,               always - false from status 400 up
    "model": "content",               when the request names a model
    "token": "aB3...",                when it's about one object
    ...                               the endpoint's own keys (fields, html, values, ...)
    "error": "One readable sentence", on an error - what cmnsd.js shows
    "errors": {"<category>": ...},    details for code: unknown_fields,
                                      validation, stale, ... (also on a
                                      partial success, e.g. unknown filters)
    "messages": [{text, level, tags}],  always - django.contrib.messages queued
                                      during this request (consumed here)
    "debug": {...}                    in DEBUG only, when the endpoint has one
  }

`api_view` makes an endpoint's 404s (unknown model, object, action, block,
suggestion field) and 405s answer in this shape too, not with an HTML page.
"""

from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.utils.translation import gettext as _


def messages_block(request):
  """The Django messages queued for this request, serialized - and marked
  read, the same as rendering them in a template: a message appears in
  exactly one response."""
  return [
    {'text': str(m), 'level': m.level_tag, 'tags': m.tags}
    for m in messages.get_messages(request)
  ]


def api_response(request, *, status=200, entry=None, obj=None, error=None, errors=None, debug=None, **payload):
  """The cmnsd API response (shape above). `entry`: the model's registry
  entry (gives `model`); `obj`: the object (gives `token`); `error`: one
  readable sentence; `errors`: {category: details}; `debug`: shown only in
  DEBUG; anything else is the endpoint's own payload."""
  data = {'ok': status < 400}
  if entry is not None:
    data['model'] = entry['name']
  if obj is not None and getattr(obj, 'token', None):
    data['token'] = obj.token
  data.update(payload)
  if error:
    data['error'] = str(error)
  if errors:
    data['errors'] = errors
  data['messages'] = messages_block(request)   # last: anything queued above is included
  if settings.DEBUG and debug is not None:
    data['debug'] = debug
  return JsonResponse(data, status=status)


def api_view(view):
  """An API endpoint: a 404 (Http404 anywhere in the view - an unknown
  model, a hidden or missing object, an unknown action/block/field) and a
  405 (wrong method) answer in the API shape instead of an HTML page."""
  @wraps(view)
  def wrapper(request, *args, **kwargs):
    try:
      response = view(request, *args, **kwargs)
    except Http404 as error:
      text = str(error) if settings.DEBUG and str(error) else _("Not found.")
      return api_response(request, status=404, error=text, errors={'not_found': True})
    if response.status_code == 405 and not isinstance(response, JsonResponse):
      return api_response(request, status=405, error=_("That method isn't allowed here."),
                          errors={'method_not_allowed': response.get('Allow', '')})
    return response
  return wrapper
