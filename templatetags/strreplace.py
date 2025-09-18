# templatetags/objreplace.py
from django import template

register = template.Library()

@register.simple_tag
def strreplace(value, what, to):
  """
  Replace substring in value.
  Usage in template:
    {% strreplace "original string" "original" "new"}
    {% strreplace app.url_format "{address}" location.address %}
  """
  return str(value).replace(str(what), str(to))
