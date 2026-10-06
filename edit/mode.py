"""
Edit mode: a page-level switch for people who may change things. While it
is on, pages render their edit controls; while it is off, a page is
exactly what every other viewer sees. See the project's edit-mode plan
(fmly: docs/EDIT-MODE-PLAN.md).

- Who: anyone holding at least one Django "change_*" permission
  (superusers hold them all). Which object may be changed is checked per
  object, by the `can_edit` template filter (templatetags/edit_mode.py) -
  the switch alone never grants anything.
- How long: the session. It stays on while moving between pages and ends
  at sign-out; never stored in Preferences, so nobody finds their pages in
  edit mode by surprise next week.
- Set by a plain form POST to cmnsd_ui:edit_mode (views/ui.py), which
  redirects back - no JS needed. Read by the context processor
  (context_processors/edit_mode.py) as `edit_mode` / `can_edit_mode`.
"""

SESSION_KEY = 'cmnsd_edit_mode'


def can_use_edit_mode(user):
  """Whether `user` gets the switch at all: signed in, active, and holding
  any change permission."""
  if not (user and user.is_authenticated and user.is_active):
    return False
  if user.is_superuser:
    return True
  return any(perm.split('.', 1)[-1].startswith('change_') for perm in user.get_all_permissions())


def is_edit_mode(request):
  """The switch is on for this request (and the user may still use it -
  a permission taken away ends edit mode on the next page)."""
  user = getattr(request, 'user', None)
  return bool(can_use_edit_mode(user) and request.session.get(SESSION_KEY))


def set_edit_mode(request, on):
  """Switch edit mode on or off for this session. Raises PermissionError
  for a user who may not use it (switching off is always allowed)."""
  if on and not can_use_edit_mode(getattr(request, 'user', None)):
    raise PermissionError("No permission to edit.")
  if on:
    request.session[SESSION_KEY] = True
  else:
    request.session.pop(SESSION_KEY, None)


def can_edit(obj, user):
  """Whether `user` may change `obj`: the object's own can_edit(user) if
  it defines one, otherwise the model's change permission."""
  if obj is None or not (user and user.is_authenticated and user.is_active):
    return False
  if hasattr(obj, 'can_edit'):
    return bool(obj.can_edit(user))
  opts = obj._meta
  return user.has_perm(f'{opts.app_label}.change_{opts.model_name}')


def require_can_edit(obj, request):
  """For @api_action methods that change something: PermissionDenied
  (the action endpoint answers 403) unless the request's user may change
  `obj` (can_edit). The edit-mode switch is UI only - the permission is
  what protects the data."""
  from django.core.exceptions import PermissionDenied
  if not can_edit(obj, getattr(request, 'user', None)):
    raise PermissionDenied("You may not change this.")
