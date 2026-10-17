"""
Mentions in Markdown: [Eric](person:<token>) - a plain link whose address is
a model's API name and an object's token - becomes a link to that object,
for a viewer who may see it. Anyone else gets the text, never a working
link - and a model can say how its hidden mentions read (a person's name
obfuscated: Person.mention_hidden_text).

  CMNSD_MENTION_MODELS = ['person', 'content', 'event', 'place']   # API names

Fail closed: without a request nobody is known, so nothing is visible - a
forgotten request costs readability, never privacy. A mention of something
hidden, of a token that doesn't exist, or without a request all look the
same: nothing tells them apart. The label itself counts too - it was typed
by the author and is in the text - so a hidden person's name is obfuscated
there as well.

Visible: filter_accessible() - the pages' own rule (status, then
visibility). The address: the object's mention_url(request) if it has one
(a person whose page this viewer may not open: their name, no link), else
get_absolute_url(). One query per model per text, not one per mention.

An empty label - [](event:<token>) - takes the object's own name when the
text is shown: always current, and as this viewer may see it - its
api_display(request) if it has one (an event names its hidden people by
initials), else str(). Hidden: only what kind of thing it is ("event") -
nothing given away.

Other schemes (mailto:, http:, unknown words) are left alone - the
sanitizer decides about them as before.
"""

import re

from django.conf import settings
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

MENTION = re.compile(r'^(?P<scheme>[a-z]+):(?P<token>[A-Za-z0-9_-]+)$')
CLASS_VISIBLE = 'mention'
CLASS_HIDDEN = 'mention mention--hidden'


def mention_models():
  """{API name: model} for the models that may be mentioned."""
  from cmnsd.api.registry import API_REGISTRY
  wanted = set(getattr(settings, 'CMNSD_MENTION_MODELS', ()))
  return {entry['name']: model for model, entry in API_REGISTRY.items() if entry['name'] in wanted}


class MentionProcessor(Treeprocessor):
  def __init__(self, md, request):
    super().__init__(md)
    self.request = request

  def run(self, root):
    models = mention_models()
    if not models:
      return
    links = []
    for link in root.iter('a'):
      match = MENTION.match(link.get('href', ''))
      if match and match['scheme'] in models:
        links.append((link, match['scheme'], match['token']))
    if not links:
      return
    visible = self._visible(models, links)
    for link, scheme, token in links:
      obj = visible.get((scheme, token))
      label = ''.join(link.itertext())
      if not label.strip():
        # Empty: its own name, now - or only its kind when hidden.
        if obj is None:
          self._as_text(link, str(models[scheme]._meta.verbose_name).lower(), CLASS_HIDDEN)   # mid-sentence
          continue
        display = getattr(obj, 'api_display', None)
        label = display(self.request) if display else str(obj)
        link.text = label
      if obj is None:
        hide = getattr(models[scheme], 'mention_hidden_text', None)
        self._as_text(link, hide(label) if hide else label, CLASS_HIDDEN)
        continue
      url = obj.mention_url(self.request) if hasattr(obj, 'mention_url') else obj.get_absolute_url()
      if url:
        link.set('href', url)
        link.set('class', CLASS_VISIBLE)
      else:
        self._as_text(link, label, CLASS_VISIBLE)   # may be seen, not opened: the name, no link

  def _visible(self, models, links):
    """{(scheme, token): object} this viewer may see - none without a request."""
    if self.request is None:
      return {}
    from cmnsd.models.access import filter_accessible
    found = {}
    tokens = {}
    for _link, scheme, token in links:
      tokens.setdefault(scheme, set()).add(token)
    for scheme, wanted in tokens.items():
      model = models[scheme]
      for obj in filter_accessible(model.objects.filter(token__in=wanted), self.request):
        found[(scheme, obj.token)] = obj
    return found

  @staticmethod
  def _as_text(link, text, css_class):
    """The link becomes plain text in a span - its children (bold, ...) go too."""
    for child in list(link):
      link.remove(child)
    link.tag = 'span'
    link.attrib.clear()
    link.set('class', css_class)
    link.text = text


class MentionExtension(Extension):
  def __init__(self, request=None, **kwargs):
    self.request = request
    super().__init__(**kwargs)

  def extendMarkdown(self, md):
    # After 'inline' (priority 20), where links are made; before external
    # links (5) - a mention's address is the site's own.
    md.treeprocessors.register(MentionProcessor(md, self.request), 'cmnsd_mentions', 6)
