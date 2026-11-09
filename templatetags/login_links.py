from django import template

from cmnsd import login_links

register = template.Library()


@register.simple_tag
def login_links_enabled():
  """{% login_links_enabled as on %} - whether the project turned login
  links on (CMNSD_LOGIN_LINKS): only then is "send login link" offered."""
  return login_links.enabled()
