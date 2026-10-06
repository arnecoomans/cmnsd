from django.views.decorators.http import require_http_methods

from .object_action import object_action
from .object_fields import object_fields
from .response import api_view


@api_view
@require_http_methods(['GET', 'POST'])
def object_endpoint(request, model, identifier, field):
  """api/<model>/<token>/<name>/ - GET reads a field (object_fields),
  POST calls an action (object_action). One URL shape, split by method -
  the dispatcher stands apart from both views, so neither imports the
  other."""
  if request.method == 'POST':
    return object_action(request, model, identifier, field)
  return object_fields(request, model, identifier, field)
