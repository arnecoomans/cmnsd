"""
Save endpoints for remembered UI state (cmnsd/ui/state.py), posted by
cmnsd.js sections.js and sort.js - answering in the API response shape
(cmnsd/views/api/response.py) - and the edit-mode switch
(cmnsd/edit/mode.py), a plain form. Routed by cmnsd/ui_urls.py.
"""

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils.translation import gettext as _
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from cmnsd.edit.mode import set_edit_mode
from cmnsd.ui.state import set_section_open, set_sort
from cmnsd.views.api.request import request_data
from cmnsd.views.api.response import api_response


@require_POST
def section_state(request):
  """POST {"key": "person.content", "open": false} - remember whether a
  collapsible section (cmnsd/section.html) is open, for the signed-in
  user (Preferences.ui_state). Signed out: 403 - visitors always get
  every section open and nothing is stored. CSRF-protected like any POST;
  cmnsd.js sends the token. Called by cmnsd.js sections.js on toggle."""
  try:
    data = request_data(request)
    set_section_open(request, data.get('key', ''), data.get('open', True))
  except PermissionError as error:
    return api_response(request, status=403, error=str(error), errors={'permission': 'sign_in'})
  except ValueError as error:  # a malformed body or an invalid key
    return api_response(request, status=400, error=str(error), errors={'request': str(error)})
  return api_response(request, key=data['key'], open=bool(data.get('open', True)))


@require_POST
def sort_state(request):
  """POST {"key": "person.content", "value": "date"} - remember a sortable
  list's order for the signed-in user (cmnsd/ui/state.py). Signed out: 403.
  Called by cmnsd.js sort.js."""
  try:
    data = request_data(request)
    set_sort(request, data.get('key', ''), data.get('value', ''))
  except PermissionError as error:
    return api_response(request, status=403, error=str(error), errors={'permission': 'sign_in'})
  except ValueError as error:
    return api_response(request, status=400, error=str(error), errors={'request': str(error)})
  return api_response(request, key=data['key'], value=data['value'])


@require_POST
def edit_mode(request):
  """POST on=1|0 (a plain form, no JS needed) - switch edit mode on or off
  for this session, then back to `next` (same site only, else '/').
  403 for a user who may not edit. CSRF-protected like any POST."""
  on = request.POST.get('on') == '1'
  try:
    set_edit_mode(request, on)
  except PermissionError as error:
    return HttpResponseForbidden(str(error))
  messages.info(request, _("Edit mode is on.") if on else _("Edit mode is off."))
  target = request.POST.get('next') or '/'
  if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
    target = '/'
  return redirect(target)
