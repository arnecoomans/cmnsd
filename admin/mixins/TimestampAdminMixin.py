class TimestampAdminMixin:
  """Adds date_created/date_modified to readonly_fields - they're already
  non-editable on the model (auto_now_add/auto_now), this just surfaces
  them in the admin form instead of hiding them entirely."""

  def get_readonly_fields(self, request, obj=None):
    return (*super().get_readonly_fields(request, obj), 'date_created', 'date_modified')
