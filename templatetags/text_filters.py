from django import template

import re

''' https://stackoverflow.com/questions/21483003/replacing-a-character-in-django-template '''
register = template.Library()


@register.filter
def replace(value, arg):
    """
    Replacing filter
    Use `{{ "aaa"|replace:"a|b" }}`
    """
    if len(arg.split('|')) != 2:
        return value

    what, to = arg.split('|')
    return value.replace(what, to)

@register.filter
def highlight(value, query):
  """
  Highlight the query in value while preserving original casing.
  Usage: {{ "First Lastname"|highlight:"last" }}
  """
  if not query:
    return value

  regex = re.compile(re.escape(query), re.IGNORECASE)

  def replace_match(match):
    return f"<b>{match.group()}</b>"  # Preserve original case

  return regex.sub(replace_match, value)

@register.filter
def split(value, delimiter=','):
    """
    Split een string op het gegeven scheidingsteken.
    Gebruik: {{ value|split:"," }}
    """
    return value.split(delimiter)

@register.simple_tag
def objreplace(value, what, to):
  """
  Replace substring in value.
  Usage in template:
    {% objreplace app.url_format "{address}" location.address %}
  """
  return str(value).replace(str(what), str(to))

@register.filter(name="whatsapp_number")
def whatsapp_number(value):
    """
    Format a phone number for WhatsApp usage:
    - Replace leading '+' with '00'
    - Remove all spaces, parentheses, and non-numeric characters
    - Return only digits and allowed prefix
    """
    if not value:
        return ""

    # 1. Replace '+' with '00' at the start
    formatted = re.sub(r'^\+', '00', str(value))

    # 2. Remove all characters except digits
    formatted = re.sub(r'[^0-9]', '', formatted)

    return formatted