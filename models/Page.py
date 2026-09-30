from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.urls import reverse

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
  """
  slug = models.SlugField(max_length=100, unique=True, help_text=_("Identifier in URL"))
  title = models.CharField(max_length=255, help_text=_("Page title"))
  body = models.TextField(blank=True, help_text=_("Markdown source, rendered via the |markdown filter"))

  class Meta:
    verbose_name = _("Page")
    verbose_name_plural = _("Pages")
    ordering = ['title']

  def __str__(self) -> str:
    return self.title

  def save(self, *args, **kwargs):
    if not self.slug and self.title:
      self.slug = slugify(self.title)
    self.full_clean()
    super().save(*args, **kwargs)

  def get_absolute_url(self):
    return reverse('cmnsd:page', kwargs={'slug': self.slug})
