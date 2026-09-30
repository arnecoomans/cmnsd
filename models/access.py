def filter_accessible(queryset, request):
  """What this viewer may see: StatusMixin.filter_status(), then
  VisibilityMixin.filter_visibility() - each applied only if the model has
  it (duck-typed, like cmnsd.api.registry.detect_capabilities).

  The one rule for "may this request see these rows" outside the API:
  VisibilityViewMixin.get_accessible_queryset() and model querysets (e.g.
  Content.objects.visible_to()) both call this, so a detail page, a file
  download and a thumbnail can't disagree. The API applies the same two
  filters through its registry (cmnsd.api.filtering.visible_queryset),
  which also honors a model opting out of the default logic."""
  model = queryset.model
  if hasattr(model, 'filter_status'):
    queryset = model.filter_status(queryset, request)
  if hasattr(model, 'filter_visibility'):
    queryset = model.filter_visibility(queryset, request)
  return queryset
