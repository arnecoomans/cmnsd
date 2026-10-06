from django.conf import settings
from django.db import models
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _


class TranslationAliasMixin(models.Model):
  """
  Adds a translation_alias field, auto-populated with every configured
  language's translation of self.name that differs from the stored name -
  makes name searchable across languages without touching the search layer
  (FilterMixin auto-discovers plain TextFields).

  This only works once translations for the *actual stored values* exist in
  the project's .po catalogs - gettext() looks up exact-string matches, and
  makemessages only extracts strings from source code, never from database
  content. "Book" -> "Boek" requires someone to hand-add a
  msgid "Book" / msgstr "Boek" entry to locale/nl/LC_MESSAGES/django.po and
  run compilemessages; this mixin surfaces that translation, it doesn't
  generate one.

  Not wired to save() automatically - the composing model's own save() must
  call self._update_translation_alias() explicitly, the same way
  HierarchyMixin's _split_compounded_name() works, since ordering relative
  to other save()-time logic (e.g. slug generation from name) matters.

  Usage:
    class Tag(TranslationAliasMixin, BaseTag):
      def save(self, *args, **kwargs):
        self._update_translation_alias()
        super().save(*args, **kwargs)
  """

  translation_alias = models.TextField(
    blank=True,
    default='',
    help_text=capfirst(_('Comma-separated translations, auto-populated on save')),
  )

  class Meta:
    abstract = True

  def _update_translation_alias(self):
    """Populate translation_alias with all available translations of self.name."""
    from django.utils.translation import override, gettext
    parts = []
    for lang_code, _label in settings.LANGUAGES:
      with override(lang_code):
        translated = gettext(self.name)
      if translated != self.name and translated not in parts:
        parts.append(translated)
    self.translation_alias = ', '.join(parts)
