from cmnsd.admin.actions import attach_set_field_actions
from cmnsd.models.mixins import StatusMixin


class StatusAdminMixin:
  """
  Adds 'status' to list_filter, without clobbering filters other mixins
  or the concrete ModelAdmin already contribute (see module docstring in
  cmnsd/admin/mixins/__init__.py for why this uses get_list_filter() rather
  than a plain list_filter = (...) attribute).

  Also offers one bulk action per Status value (mark_status_c,
  mark_status_p, mark_status_r, mark_status_x - "Mark as Concept"/
  "Published"/"Revoked"/"Deleted"), attached below. Not auto-registered -
  wire the ones you want explicitly:

    class TagAdmin(StatusAdminMixin, admin.ModelAdmin):
      actions = ['mark_status_p', 'mark_status_r']
  """

  def get_list_filter(self, request):
    return (*super().get_list_filter(request), 'status')


attach_set_field_actions(StatusAdminMixin, 'status', StatusMixin.Status.choices)
