"""
Finding what an API request is about - shared by every cmnsd API endpoint:
the model from its registered name, and one object of it that the viewer
may see.
"""

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404

from cmnsd.api.filtering import visible_queryset
from cmnsd.api.registry import API_REGISTRY


def resolve_model(model_name):
  """(model class, registry entry) for an API name ('content'), else
  Http404. API_REGISTRY is keyed by class and the URL only has the name -
  a linear scan of a small registry; a name-keyed index only if this ever
  shows up in profiling."""
  for model_cls, entry in API_REGISTRY.items():
    if entry['name'] == model_name:
      return model_cls, entry
  raise Http404(f"'{model_name}' is not an API-registered model.")


def get_visible_object(request, model_cls, entry, identifier):
  """The object `identifier` names, among those this viewer may see
  (status + visibility, visible_queryset) - else Http404: hidden and
  missing look the same. `identifier` is the token (docs/api.md
  #Identification); in DEBUG only, an all-digits
  value is tried as a pk - a manual-testing convenience; nothing builds
  such a URL."""
  lookup = {'pk': identifier} if settings.DEBUG and identifier.isdigit() else {'token': identifier}
  return get_object_or_404(visible_queryset(model_cls, entry, request), **lookup)
