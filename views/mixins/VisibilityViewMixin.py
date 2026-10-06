from cmnsd.models.access import filter_accessible


class VisibilityViewMixin:
  """
  Applies what a viewer may see to a queryset: get_accessible_queryset()
  for status + visibility (use this), get_visible_queryset() for
  visibility alone. The model-level visibility logic (public always visible; community if
  authenticated; family if the current user owns the row or is in
  <owner>.preferences.family, per CMNSD_VISIBILITY_FAMILY_LOOKUP_STORAGE;
  private only to the owner) already exists and is fully correct, this is
  just the missing view-layer wiring.

  Not an implicit get_queryset() override - composing views can have
  visibility-independent base querysets to build first (e.g. an extra
  `private=True` exclusion that has nothing to do with per-user
  visibility). Call get_accessible_queryset() explicitly from your own
  get_queryset():

    class PersonDetailView(VisibilityViewMixin, DetailView):
      def get_queryset(self):
        return self.get_accessible_queryset(Person.objects.optimized())

  For a DetailView, this is also the 404 enforcement - no separate check
  needed. Django's own SingleObjectMixin.get_object() already raises a
  generic Http404 ("No <Model> found matching the query") when the
  requested pk/slug isn't present in get_queryset() - since an invisible
  object is simply excluded from the filtered queryset, requesting it 404s
  the same way a nonexistent pk would, with no hint as to *why* it's
  inaccessible.
  """

  def get_visible_queryset(self, queryset):
    """Visibility only. For deciding what a viewer may see, use
    get_accessible_queryset() - this one lets a concept or deleted row
    through."""
    return queryset.model.filter_visibility(queryset, self.request)

  def get_accessible_queryset(self, queryset):
    """Status AND visibility (cmnsd.models.access.filter_accessible) - what
    a detail/list view should use. Visibility alone isn't enough: a
    deleted or concept row would still be served by its URL."""
    return filter_accessible(queryset, self.request)
