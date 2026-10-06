from django import template

from cmnsd.ui.state import is_section_open, remembers_sections

register = template.Library()


@register.simple_tag(takes_context=True)
def section_open(context, key):
  """{% section_open 'person.content' as is_open %} - whether this viewer
  keeps that section open (Preferences.ui_state; default open; always
  open when signed out)."""
  return is_section_open(context.get('request'), key)


@register.simple_tag(takes_context=True)
def sections_collapsible(context):
  """{% sections_collapsible as collapsible %} - signed-in users get
  collapsible, remembered sections; visitors get them plain and open."""
  return remembers_sections(context.get('request'))
