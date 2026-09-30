import re

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class SlugMixin(models.Model):
  """Adds a unique slug, generated from get_slug_source() on save.

  Uniqueness: a taken slug gets -2, -3, ... appended.

  slug_follows_source (class attribute):
    False (default) - the slug is set once, when empty, and never changes
            afterwards: right for anything whose URL uses the slug (Person).
    True  - regenerated whenever the source no longer matches: right for a
            slug that only names something internal (Content's filename),
            where a stale slug is worse than a changed one.
  """
  slug_follows_source = False
  # Slugs that would collide with fixed URL segments next to the slug
  # (e.g. Content's <token>/file/): such a base gets -2 like a taken slug.
  reserved_slugs = ()
  # Leaves room for a -N suffix and for use inside a file path.
  SLUG_BASE_MAX_LENGTH = 200

  slug = models.SlugField(
    max_length=255, unique=True, blank=True,
    help_text=_("A unique identifier, generated from the name"),
  )

  class Meta:
    abstract = True

  def get_slug_source(self):
    """What the slug is generated from - override per model."""
    return str(self)

  def _slug_base(self):
    base = slugify(self.get_slug_source())[:self.SLUG_BASE_MAX_LENGTH].strip('-')
    return base or self._meta.model_name

  def _generate_unique_slug(self, base):
    slug, n = base, 2
    others = self.__class__._default_manager.exclude(pk=self.pk)
    while slug in self.reserved_slugs or others.filter(slug=slug).exists():
      slug = f"{base}-{n}"
      n += 1
    return slug

  def _slug_matches_source(self, base):
    return bool(re.fullmatch(rf'{re.escape(base)}(-\d+)?', self.slug or ''))

  def save(self, *args, **kwargs):
    if not self.slug:
      self.slug = self._generate_unique_slug(self._slug_base())
    elif self.slug_follows_source:
      base = self._slug_base()
      if not self._slug_matches_source(base):
        self.slug = self._generate_unique_slug(base)
    super().save(*args, **kwargs)
