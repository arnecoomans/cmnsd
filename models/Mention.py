"""
Mentions (issue #470): an index of what a text refers to - a biography, a
description, a comment saying [Eric](person:<token>) (cmnsd/markdown/
mentions.py) - so "what mentions Eric" is a query, not a search through
every text. A shadow of the text: rebuilt from it on every save
(MentionableSourceMixin), never edited by hand.

What it records is what the text *says*, whoever may read it; who sees
which mention is decided when it's shown (mentioned_in(): the sources this
viewer may see). A mention of a token that doesn't exist isn't recorded;
rows go with their source or target (a delete removes them - a generic
link has no on_delete of its own).

No role here: the role of a person on an item is a link of its own
(issue #471), not a text's reference.
"""

import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

# [label](scheme:token) - in the stored text, before Markdown.
MENTION_IN_TEXT = re.compile(r'\]\((?P<scheme>[a-z]+):(?P<token>[A-Za-z0-9_-]+)\)')


class Mention(models.Model):
  source_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+')
  source_id = models.PositiveIntegerField()
  source = GenericForeignKey('source_content_type', 'source_id')
  # Which of the source's text fields says it ("biography", "body").
  source_field = models.CharField(max_length=50)
  target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+')
  target_id = models.PositiveIntegerField()
  target = GenericForeignKey('target_content_type', 'target_id')
  date_created = models.DateTimeField(auto_now_add=True)

  class Meta:
    constraints = [
      models.UniqueConstraint(
        fields=['source_content_type', 'source_id', 'source_field', 'target_content_type', 'target_id'],
        name='cmnsd_mention_once',
      ),
    ]
    indexes = [
      models.Index(fields=['target_content_type', 'target_id'], name='cmnsd_mention_target'),
      models.Index(fields=['source_content_type', 'source_id'], name='cmnsd_mention_source'),
    ]

  def __str__(self):
    return f"{self.source_content_type.model} {self.source_id}.{self.source_field} → {self.target_content_type.model} {self.target_id}"


def mentions_in(text):
  """{(scheme, token)} the text refers to - for the mentionable kinds."""
  from cmnsd.markdown.mentions import mention_models
  kinds = mention_models()
  return {(m['scheme'], m['token']) for m in MENTION_IN_TEXT.finditer(text or '') if m['scheme'] in kinds}


def sync_mentions(source):
  """Bring source's Mention rows in line with its text fields
  (source.mention_fields): add what's new, remove what's gone - nothing
  when nothing changed. A token that doesn't exist isn't recorded; the
  source mentioning itself isn't either, nor what it says it belongs to:
  source.mention_excluded_targets() -> [(model, pks)], if it has one (a
  transcript's own item - "mentioned in the transcript of X" on X's page
  adds nothing)."""
  from cmnsd.markdown.mentions import mention_models
  kinds = mention_models()
  source_type = ContentType.objects.get_for_model(source)
  excluded = set()
  for model, pks in (source.mention_excluded_targets() if hasattr(source, 'mention_excluded_targets') else ()):
    model_type = ContentType.objects.get_for_model(model)
    excluded |= {(model_type.pk, pk) for pk in pks}
  wanted = set()
  for field in source.mention_fields:
    found = mentions_in(getattr(source, field, ''))
    by_scheme = {}
    for scheme, token in found:
      by_scheme.setdefault(scheme, set()).add(token)
    for scheme, tokens in by_scheme.items():
      model = kinds[scheme]
      target_type = ContentType.objects.get_for_model(model)
      for pk in model.objects.filter(token__in=tokens).values_list('pk', flat=True):
        if not (target_type == source_type and pk == source.pk) and (target_type.pk, pk) not in excluded:
          wanted.add((field, target_type.pk, pk))
  existing = {
    (row.source_field, row.target_content_type_id, row.target_id): row.pk
    for row in Mention.objects.filter(source_content_type=source_type, source_id=source.pk)
  }
  gone = [pk for key, pk in existing.items() if key not in wanted]
  if gone:
    Mention.objects.filter(pk__in=gone).delete()
  new = [key for key in wanted if key not in existing]
  if new:
    Mention.objects.bulk_create([
      Mention(source_content_type=source_type, source_id=source.pk, source_field=field, target_content_type_id=type_pk, target_id=pk)
      for field, type_pk, pk in new
    ])


class MentionableSourceMixin(models.Model):
  """A model whose text fields may mention things: their mentions are
  indexed on every save (cmnsd.models.Mention).

    class Person(MentionableSourceMixin, ...):
      mention_fields = ('biography',)

  A save(update_fields=...) without any of them doesn't touch the index.
  Bulk updates (queryset.update) skip save() - rebuild with
  manage.py mentions_index."""

  mention_fields = ()

  class Meta:
    abstract = True

  def save(self, *args, **kwargs):
    super().save(*args, **kwargs)
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and not set(update_fields) & set(self.mention_fields):
      return
    sync_mentions(self)


@receiver(post_delete)
def forget_mentions(sender, instance, **kwargs):
  """A deleted source or target takes its Mention rows along - only for the
  models that can be either, so other deletes cost nothing."""
  from cmnsd.markdown.mentions import mention_models
  if sender is Mention:
    return
  is_source = issubclass(sender, MentionableSourceMixin)
  is_target = sender in mention_models().values()
  if not (is_source or is_target):
    return
  kind = ContentType.objects.get_for_model(sender)
  query = models.Q()
  if is_source:
    query |= models.Q(source_content_type=kind, source_id=instance.pk)
  if is_target:
    query |= models.Q(target_content_type=kind, target_id=instance.pk)
  Mention.objects.filter(query).delete()


def mentioned_in(obj, request):
  """[{'source', 'fields', 'kind', 'excerpts', 'more'}] - the texts
  mentioning obj that this viewer may see (excerpts: the words around each
  mention, more: those beyond the shown ones - cmnsd.markdown.mentions.
  mention_excerpts): one query per kind of source. Visible by the source
  model's own rule - its mention_sources_for(queryset, request) if it has
  one (a comment only with a target the viewer may see too), else
  filter_accessible(). Without a request: none (fail closed, as the
  mentions themselves). Ordered by kind as in CMNSD_MENTION_MODELS, other
  sources (comments) last; within a kind by their own ordering. Kept on
  obj for the rest of the request (a section's count and its body)."""
  if request is None:
    return []
  cache = getattr(obj, '_mentioned_in', None)
  if cache is not None and cache[0] is request:
    return cache[1]
  from cmnsd.api.registry import API_REGISTRY
  from cmnsd.markdown.mentions import mention_models
  from cmnsd.markdown.mentions import mention_excerpts
  from cmnsd.models.access import filter_accessible
  target_type = ContentType.objects.get_for_model(obj)
  target_kind = API_REGISTRY.get(type(obj), {}).get('name') or obj._meta.model_name
  fields_of = {}
  for type_pk, source_pk, field in Mention.objects.filter(target_content_type=target_type, target_id=obj.pk).values_list('source_content_type', 'source_id', 'source_field'):
    fields_of.setdefault(type_pk, {}).setdefault(source_pk, []).append(field)
  order = list(mention_models())
  results = []
  for type_pk, sources in fields_of.items():
    model = ContentType.objects.get_for_id(type_pk).model_class()
    if model is None:
      continue
    queryset = model.objects.filter(pk__in=sources)
    hook = getattr(model, 'mention_sources_for', None)
    visible = hook(queryset, request) if hook else filter_accessible(queryset, request)
    kind = API_REGISTRY.get(model, {}).get('name') or model._meta.model_name
    rank = order.index(kind) if kind in order else len(order)
    for source in visible:
      fields = sorted(sources[source.pk])
      # What it says: the words around each mention, as this viewer may read them.
      excerpts, more = [], 0
      for field in fields:
        found, extra = mention_excerpts(getattr(source, field, ''), target_kind, obj.token, request)
        excerpts += found
        more += extra
      results.append({'source': source, 'fields': fields, 'kind': kind, 'rank': rank, 'excerpts': excerpts, 'more': more})
  results.sort(key=lambda row: row['rank'])
  obj._mentioned_in = (request, results)
  return results
