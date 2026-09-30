from django import template
from django.template import TemplateSyntaxError
from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe

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
  Highlight the query in value while preserving original casing. The wrapper
  tag is CMNSD_HIGHLIGHT_TAG, not a filter argument - Django's {{ value|filter:arg }}
  syntax only ever supplies one argument, so a template can't pass a tag
  choice here even if this took one.
  Usage: {{ "First Lastname"|highlight:"last" }}
  """
  if not query:
    return value

  highlight_tag = getattr(settings, 'CMNSD_HIGHLIGHT_TAG', 'mark')

  # value/query are escaped first, then the highlight tag is injected around
  # the (now escaped) match, then the whole thing is marked safe - so any
  # HTML-special characters actually in value/query stay inert, and only the
  # tag we're inserting ourselves renders as real HTML.
  escaped_value = escape(str(value))
  regex = re.compile(re.escape(escape(str(query))), re.IGNORECASE)

  def replace_match(match):
    return f"<{highlight_tag}>{match.group()}</{highlight_tag}>"  # Preserve original case

  return mark_safe(regex.sub(replace_match, escaped_value))


# A tag or an HTML entity - kept intact by highlight_search, so a term
# never matches inside markup (an href, a class) or splits an &amp;.
_TAG_OR_ENTITY = re.compile(r'(<[^>]*>|&#?\w+;)')


@register.tag(name='highlight_search')
def do_highlight_search(parser, token):
  """
  Mark every search term in the rendered block's visible text.
  Usage: {% highlight_search search_query %}...{% endhighlight_search %}

  Unlike |highlight, this works on already-rendered HTML: the block is
  rendered first, then terms are wrapped only in the text between tags,
  so existing markup (a link, the called-name <mark> from |highlight)
  survives and the two highlights can overlap. The query is split on
  whitespace like the list search (cmnsd/api/filtering.py), and each
  term is marked on its own. Blank/missing query = block unchanged, so
  it's safe in templates also rendered outside a search.

  Wrapper: CMNSD_HIGHLIGHT_TAG with class="search-hit", styled apart
  from a plain |highlight mark.
  """
  bits = token.split_contents()
  if len(bits) != 2:
    raise TemplateSyntaxError(f"'{bits[0]}' takes exactly one argument: the search query.")
  nodelist = parser.parse(('endhighlight_search',))
  parser.delete_first_token()
  return HighlightSearchNode(parser.compile_filter(bits[1]), nodelist)


class HighlightSearchNode(template.Node):
  def __init__(self, query, nodelist):
    self.query = query
    self.nodelist = nodelist

  def render(self, context):
    output = self.nodelist.render(context)
    terms = str(self.query.resolve(context) or '').split()
    if not terms:
      return output
    tag = getattr(settings, 'CMNSD_HIGHLIGHT_TAG', 'mark')
    # Longest first, so "eric" wins over "e" where both could match. Terms
    # are escaped to compare against the (escaped) rendered text.
    terms = sorted({escape(term) for term in terms}, key=len, reverse=True)
    pattern = re.compile('|'.join(re.escape(term) for term in terms), re.IGNORECASE)

    def mark(match):
      return f'<{tag} class="search-hit">{match.group()}</{tag}>'

    # split() with a capture group: odd indexes are the tags/entities.
    parts = _TAG_OR_ENTITY.split(output)
    return mark_safe(''.join(
      part if index % 2 else pattern.sub(mark, part)
      for index, part in enumerate(parts)
    ))


@register.simple_tag
def str_replace(value, what, to):
  """
  Replace substring in value.
  Usage in template:
    {% str_replace app.url_format "{address}" location.address %}
  """
  return str(value).replace(str(what), str(to))

@register.filter(name="without_value")
def without_value(value, arg):
    """
    Exclude all items equal to arg from a list.
    Usage: {{ my_list|without_value:some_value }}
    """
    if not isinstance(value, list):
      return value
    return [v for v in value if v != arg]

@register.filter(name="prepend")
def prepend(value, arg):
    """
    Prepend arg to value.
    Usage: {{ value|prepend:"string_to_prepend" }}
    """
    return str(arg) + str(value)

@register.filter(name="get_item")
def get_item(dictionary, key):
  """
  Get an item from a dictionary using a key.
  Usage: {{ my_dict|get_item:"my_key" }}
  """
  return dictionary.get(key, '')
