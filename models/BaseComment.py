from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from cmnsd.models.mixins import (
  TimestampMixin, TokenMixin, StatusMixin, OwnershipMixin
)


class BaseComment(TimestampMixin, TokenMixin, StatusMixin, OwnershipMixin, models.Model):
  name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Name"), help_text=f"{_('Define a name for this comment.')}, {_('optional')}" )
  content = models.TextField(verbose_name=_("Content"), help_text=f"{_('Define the content of this comment.')}, {_('required')}" )
  # token, ownership, status and visibility fields are provided by mixins

  # GenericForeignKey: works against any model without a migration on this
  # one when a new commentable model shows up later. The trade-off (vs a
  # nullable FK per model) is no DB-level referential integrity on this
  # relation - target_id isn't a real FK, so nothing at the DB layer stops
  # it pointing at a row that's since been deleted.
  target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
  target_id = models.PositiveIntegerField()
  target = GenericForeignKey('target_content_type', 'target_id')

  class Meta:
    abstract = True
    verbose_name = _("Comment")
    verbose_name_plural = _("Comments")

  def __str__(self) -> str:
    owner = self.user.username if self.user else _('Unknown')
    return f"{ self.name } by { owner }" if self.name else f"{ _('Comment') } #{self.id} by { owner }"

  # No custom clean() needed for "must be attached to something" - target_id
  # and target_content_type are both non-nullable fields already, so
  # full_clean()'s own field-level validation already rejects a missing
  # target (and a GenericForeignKey is structurally single-target, so
  # "attached to two things at once" isn't representable in the first place).

  def save(self, *args, **kwargs):
    self.full_clean()
    super().save(*args, **kwargs)
