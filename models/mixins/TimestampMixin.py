from django.db import models


class TimestampMixin(models.Model):
  """Adds created/modified timestamps."""
  date_created = models.DateTimeField(auto_now_add=True)
  date_modified = models.DateTimeField(auto_now=True)

  class Meta:
    abstract = True
