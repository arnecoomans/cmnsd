class HierarchyAdminMixin:
  """Adds display_name to list_display, so the admin list shows the full
  "Parent: Child" chain instead of just the leaf name. Adds to whatever
  list_display already has - doesn't remove/replace 'name' if the concrete
  admin already lists it.

  Deliberately doesn't set raw_id_fields for 'parent' here: Django's
  ModelAdmin has no get_raw_id_fields() hook to override, only the plain
  raw_id_fields attribute - composing that safely across multiple mixins
  isn't possible the way get_list_filter()/get_readonly_fields() are, so
  it's left for the concrete ModelAdmin to set directly if the list grows
  large enough to need it."""

  def get_list_display(self, request):
    return (*super().get_list_display(request), 'display_name')
