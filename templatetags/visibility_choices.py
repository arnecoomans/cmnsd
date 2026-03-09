from django import template
from cmnsd.models import VisibilityModel

register = template.Library()

@register.simple_tag
def visibility_choices():
  return VisibilityModel.get_visibility_choices()
