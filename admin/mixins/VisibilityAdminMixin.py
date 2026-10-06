from cmnsd.admin.actions import attach_set_field_actions
from cmnsd.models.mixins import VisibilityMixin


class VisibilityAdminMixin:
  """
  Adds 'visibility' to list_filter - see StatusAdminMixin for why this
  is a get_list_filter() override rather than a plain attribute.

  Also offers one bulk action per Visibility value (mark_visibility_p,
  mark_visibility_c, mark_visibility_f, mark_visibility_q - "Mark as
  Public"/"Community"/"Family"/"Private"), attached below. Not
  auto-registered - wire the ones you want explicitly:

    class TagAdmin(VisibilityAdminMixin, admin.ModelAdmin):
      actions = ['mark_visibility_p', 'mark_visibility_q']
  """

  def get_list_filter(self, request):
    return (*super().get_list_filter(request), 'visibility')


attach_set_field_actions(VisibilityAdminMixin, 'visibility', VisibilityMixin.Visibility.choices)
