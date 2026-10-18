from django.apps import apps
from django.core.management.base import BaseCommand

from cmnsd.models import MentionableSourceMixin
from cmnsd.models.Mention import sync_mentions


class Command(BaseCommand):
  help = (
    "Build the index of mentions (cmnsd.models.Mention) from every text that "
    "can mention something (MentionableSourceMixin.mention_fields): once after "
    "installing, or after texts changed without save() (a bulk update). Safe to "
    "repeat - it only adds what's missing and removes what's gone."
  )

  def handle(self, *args, **options):
    from cmnsd.models import Mention
    before = Mention.objects.count()
    for model in apps.get_models():
      if not issubclass(model, MentionableSourceMixin) or not model.mention_fields:
        continue
      count = 0
      for source in model.objects.all().iterator():
        sync_mentions(source)
        count += 1
      self.stdout.write(f"{model._meta.label}: {count} checked")
    self.stdout.write(self.style.SUCCESS(f"Mentions: {before} before, {Mention.objects.count()} now."))
