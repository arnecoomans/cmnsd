from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.urls import reverse

from cmnsd.ui.languages import default_language
from cmnsd.models.mixins import TimestampMixin, TokenMixin, StatusMixin


class Page(TimestampMixin, TokenMixin, StatusMixin, models.Model):
  """
  Generic static/informational page (cookie statement, privacy policy,
  terms, about, ...) - a slug-addressed title + markdown body, rendered
  through cmnsd's `|markdown` filter. Concrete (not abstract): every
  cmnsd-consuming project gets the same table for free, no per-project
  subclass needed - unlike Tag/Comment/Preferences, this has no plausible
  per-project field variation (no OwnershipMixin/VisibilityMixin either:
  these are public, admin-managed pages, not user-scoped content).

  Multilingual: one row per page per language - (slug, language) is
  unique, so a page and its translations share one address
  (/pages/<slug>/). The view shows the visitor's language, else the site's
  default (cmnsd.views.pages.page_detail) - an untranslated page simply
  shows in the default language.
  """
  slug = models.SlugField(max_length=100, help_text=_("Identifier in URL - the same for each translation"))
  language = models.CharField(
    max_length=10, choices=settings.LANGUAGES, default=default_language,
    help_text=_("Language this page is written in"),
  )
  title = models.CharField(max_length=255, help_text=_("Page title"))
  body = models.TextField(blank=True, help_text=_("Markdown source, rendered via the |markdown filter"))

  class Meta:
    verbose_name = _("Page")
    verbose_name_plural = _("Pages")
    ordering = ['slug', 'language']
    constraints = [
      models.UniqueConstraint(fields=['slug', 'language'], name='cmnsd_page_unique_slug_language'),
    ]

  def __str__(self) -> str:
    return f"{self.title} ({self.language})"

  def save(self, *args, **kwargs):
    if not self.slug and self.title:
      self.slug = slugify(self.title)
    self.full_clean()
    super().save(*args, **kwargs)

  def get_absolute_url(self):
    return reverse('cmnsd:page', kwargs={'slug': self.slug})
