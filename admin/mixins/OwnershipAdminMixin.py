class OwnershipAdminMixin:
  """
  Pre-fills the 'user' field with the current user when adding a new
  object in the admin, without forcing it - staff can still pick a
  different owner (e.g. entering content on behalf of another family
  member). Django only calls get_changeform_initial_data on the add
  form, so an existing owner is never touched on change.
  """

  def get_changeform_initial_data(self, request):
    initial = super().get_changeform_initial_data(request)
    initial.setdefault('user', request.user.pk)
    return initial
