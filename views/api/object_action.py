import minify_html

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.utils.translation import gettext as _
from django.template import TemplateDoesNotExist
from django.template.loader import select_template

from .lookup import get_visible_object, resolve_model
from .request import request_data
from .response import api_response


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
  markup, the same as fields (docs/api.md #Actions)."""
  model_cls, entry = resolve_model(model)
  config = entry['actions'].get(action)
  if config is None:
    raise Http404(f"'{action}' is not an action of '{entry['name']}'.")
  if config.get('requires_auth', True) and not request.user.is_authenticated:
    return api_response(request, status=403, entry=entry, error=_("Sign in to do this."), errors={'permission': 'sign_in'})

  obj = get_visible_object(request, model_cls, entry, identifier)

  try:
    data = request_data(request)
    result = getattr(obj, action)(request=request, data=data) or {}
  except PermissionDenied as error:
    return api_response(request, status=403, entry=entry, obj=obj, error=str(error) or _("Not allowed."), errors={'permission': True})
  except ValidationError as error:
    return api_response(request, status=400, entry=entry, obj=obj, error=' '.join(error.messages), errors={'validation': error.messages})
  except ValueError as error:  # malformed body
    return api_response(request, status=400, entry=entry, obj=obj, error=str(error), errors={'request': str(error)})

  payload = {'action': action}
  template = _action_template(entry, action)
  if template:
    context = {entry['name']: obj, 'result': result, 'request': request}
    payload['html'] = minify_html.minify(template.render(context, request), minify_js=True, minify_css=True)
  return api_response(request, entry=entry, obj=obj, **payload)


def _action_template(entry, action):
  """<model>/actions/<action>.html, else the shared actions/<action>.html
  (e.g. add_comment, the same for every commentable model), else None."""
  try:
    return select_template([f"{entry['name']}/actions/{action}.html", f"actions/{action}.html"])
  except TemplateDoesNotExist:
    return None
