from cmnsd.edit.mode import can_use_edit_mode, is_edit_mode


def edit_mode(request):
  """`can_edit_mode`: show the Edit switch; `edit_mode`: it's on - pages
  render their edit controls (each also checks `obj|can_edit:request`).
  Cheap for visitors: nothing is looked up when signed out."""
  user = getattr(request, 'user', None)
  if not (user and user.is_authenticated):
    return {'can_edit_mode': False, 'edit_mode': False}
  return {'can_edit_mode': can_use_edit_mode(user), 'edit_mode': is_edit_mode(request)}
