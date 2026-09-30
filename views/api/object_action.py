import json

import minify_html

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.template import TemplateDoesNotExist
from django.template.loader import select_template
from django.views.decorators.http import require_http_methods

from cmnsd.api.filtering import visible_queryset

from .object_fields import _messages_block, _resolve_model, object_fields


def _request_data(request):
  """JSON body, or form fields - cmnsd.js sends JSON; a plain form post
  works too."""
  if request.content_type == 'application/json':
    data = json.loads(request.body or b'{}')
    if not isinstance(data, dict):
      raise ValueError("Expected a JSON object.")
    return data
  return request.POST.dict()


def _error(status, message, entry=None, obj=None, **extra):
  response = {'ok': False, 'error': message, **extra}
  if entry is not None:
    response['model'] = entry['name']
  if obj is not None:
    response['token'] = obj.token
  return JsonResponse(response, status=status)


def object_action(request, model, identifier, action):
  """POST api/<model>/<token>/<action>/ - call an @api_action method.

  Order of checks: the action must be declared (@api_action) on this model
  - an undeclared name is 404, nothing is callable by accident; signed-out
  requests get 403 when the action requires_auth; the object must be in
  the viewer's visible queryset (status + visibility), else 404 - you
  can't act on what you can't see. Anything finer (only the author may
  edit) is the action's own check: it raises PermissionDenied (403) or
  ValidationError (400). CSRF applies like any POST.

  The action is called as method(request=request, data=<dict>) and returns
  a dict. The response packs the rendered <model>/actions/<action>.html
  (falling back to actions/<action>.html) with context {<model>: obj,
  'result': <that dict>, 'request'} as `html` - so the JS only inserts
  markup, the same as fields (docs/cmnsd_api_design.md #Actions)."""
  model_cls, entry = _resolve_model(model)
  config = entry['actions'].get(action)
  if config is None:
    raise Http404(f"'{action}' is not an action of '{entry['name']}'.")
  if config.get('requires_auth', True) and not request.user.is_authenticated:
    return _error(403, "Sign in to do this.", entry)

  lookup = {'pk': identifier} if settings.DEBUG and identifier.isdigit() else {'token': identifier}
  obj = get_object_or_404(visible_queryset(model_cls, entry, request), **lookup)

  try:
    data = _request_data(request)
    result = getattr(obj, action)(request=request, data=data) or {}
  except PermissionDenied as error:
    return _error(403, str(error) or "Not allowed.", entry, obj)
  except ValidationError as error:
    return _error(400, ' '.join(error.messages), entry, obj, errors=error.messages)
  except ValueError as error:  # malformed body
    return _error(400, str(error), entry, obj)

  response = {'ok': True, 'model': entry['name'], 'token': obj.token, 'action': action}
  template = _action_template(entry, action)
  if template:
    context = {entry['name']: obj, 'result': result, 'request': request}
    response['html'] = minify_html.minify(template.render(context, request), minify_js=True, minify_css=True)
  response['messages'] = _messages_block(request)
  return JsonResponse(response)


def _action_template(entry, action):
  """<model>/actions/<action>.html, else the shared actions/<action>.html
  (e.g. add_comment, the same for every commentable model), else None."""
  try:
    return select_template([f"{entry['name']}/actions/{action}.html", f"actions/{action}.html"])
  except TemplateDoesNotExist:
    return None


@require_http_methods(['GET', 'POST'])
def object_endpoint(request, model, identifier, field):
  """api/<model>/<token>/<name>/ - GET reads a field (object_fields),
  POST calls an action (object_action). One URL shape, split by method."""
  if request.method == 'POST':
    return object_action(request, model, identifier, field)
  return object_fields(request, model, identifier, field)
