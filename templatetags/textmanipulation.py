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
    return f"<span class='highlight'>{match.group()}</span>"  # Preserve original case

  return regex.sub(replace_match, value)

@register.filter
def split(value, delimiter=','):
    """
    Split een string op het gegeven scheidingsteken.
    Gebruik: {{ value|split:"," }}
    """
    return value.split(delimiter)