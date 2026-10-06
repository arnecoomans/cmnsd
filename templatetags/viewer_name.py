from django import template

register = template.Library()


@register.filter
def viewer_name(obj, request):
  """{{ obj|viewer_name:request }} - an object's name as this viewer may
  see it: its api_display(request) if the model defines one (e.g. an event
  names only the people the viewer may see - the rest obfuscated), else
  str(). Use it wherever a name of an arbitrary object is shown - the API
  list does the same (cmnsd/views/api/object_list.py)."""
  display = getattr(obj, 'api_display', None)
  return display(request) if display else str(obj)
