from django.db import models
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _


class TranslationAliasMixin(models.Model):
  """Mixin that adds an `aliases` field and auto-populates it with translations.

  On each save, iterates over settings.LANGUAGES, activates each language,
  translates `self.name` via gettext, and stores any results that differ from
  the stored name as a comma-separated string in `aliases`.

  This makes the name searchable in all configured languages without any changes
  to the search layer — FilterMixin auto-discovers the `aliases` TextField.

  Usage:
    class Category(TranslationAliasMixin, BaseModel):
        name = models.CharField(...)

  After adding the mixin, run makemigrations. Run the management command
  `update_translation_aliases` after compilemessages to refresh stale aliases.
  """

  aliases = models.TextField(
    blank=True,
    default='',
    help_text=capfirst(_('comma-separated translations, auto-populated on save')),
  )

  class Meta:
    abstract = True

  def _update_aliases(self):
    """Populate aliases with all available translations of self.name."""
    from django.utils.translation import get_language, activate, gettext
    from django.conf import settings
    current = get_language()
    parts = []
    for lang_code, _ in settings.LANGUAGES:
      activate(lang_code)
      translated = gettext(self.name)
      if translated != self.name and translated not in parts:
        parts.append(translated)
    if current:
      activate(current)
    self.aliases = ', '.join(parts)
