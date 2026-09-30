from django.db import models
from django.conf import settings


class OwnershipMixin(models.Model):
  """
  Adds a required FK to the user who owns the record.
  on_delete=PROTECT: a user cannot be deleted while they still own
  records - ownership must be reassigned first, so archival content
  never silently loses its owner.
  Not set here: assigning the current user on create is a view/admin
  concern - see OwnershipViewMixin / OwnershipAdminMixin.
  """
  user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.PROTECT,
    blank=True,
    related_name="%(class)s_created_by",
  )

  class Meta:
    abstract = True
