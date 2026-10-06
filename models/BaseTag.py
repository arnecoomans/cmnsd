from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify

from cmnsd.models.mixins import TokenMixin, OwnershipMixin, HierarchyMixin, TranslationAliasMixin


class BaseTag(TokenMixin, OwnershipMixin, HierarchyMixin, TranslationAliasMixin, models.Model):
  slug                = models.CharField(max_length=64, help_text=f"{ _('Identifier in URL') } ({ _('automatically generated') })")
  name                = models.CharField(max_length=128, help_text=_('Name of tag'))
  description         = models.TextField(blank=True, help_text=_('Description of this tag, why it is relevant'))
  # parent (self-FK, PROTECT), compound-name splitting, display_name() and
  # ancestors() all come from HierarchyMixin. translation_alias comes from
  # TranslationAliasMixin.

  class Meta:
    abstract = True
    verbose_name = _("Tag")
    verbose_name_plural = _("Tags")
    constraints = [
      # nulls_distinct=False: SQL treats NULL != NULL by default, so a plain
      # UNIQUE(parent, name) would never catch duplicates among root-level
      # tags (parent is NULL) - which is most of them. This makes NULL
      # parents compare as equal for uniqueness purposes too.
      models.UniqueConstraint(fields=['parent', 'name'], name='%(app_label)s_%(class)s_unique_name_per_parent', nulls_distinct=False),
      models.UniqueConstraint(fields=['parent', 'slug'], name='%(app_label)s_%(class)s_unique_slug_per_parent', nulls_distinct=False),
    ]
    ordering = ['parent__name', 'name']

  def __str__(self) -> str:
    return self.display_name()

  def save(self, *args, **kwargs):
    self._split_compounded_name()
    if not self.name and self.slug:
      # Build a name from the slug if no name is provided
      self.name = self.slug.replace('-', ' ').replace('_', ' ').replace('+', ' ').title()
    if not self.slug and self.name:
      # Build a slug from the name if no slug is provided
      self.slug = slugify(self.name)
    # After name is fully resolved (post-split, post slug-fallback) so the
    # alias is built from the actual leaf name, not a pre-split compound one.
    self._update_translation_alias()
    self.full_clean()
    super().save(*args, **kwargs)
