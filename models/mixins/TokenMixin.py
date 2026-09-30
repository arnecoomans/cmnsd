import string
import secrets

from django.db import models
from django.utils.translation import gettext_lazy as _


def generate_public_id(length=10):
  """Generate a short, URL-safe public ID (not guessable)."""
  alphabet = string.ascii_letters + string.digits
  return ''.join(secrets.choice(alphabet) for _ in range(length))


class TokenMixin(models.Model):
  """Adds a unique, URL-safe public token."""
  # Exposed as a class attribute so migrations referencing
  # cmnsd.models.mixins.TokenMixin.generate_public_id resolve correctly
  # (cmnsd.models.mixins.TokenMixin resolves to this class, not the module).
  generate_public_id = generate_public_id

  token = models.CharField(
    max_length=20,
    unique=True,
    editable=False,
    blank=True,
    default=generate_public_id,
    help_text=_("Short unique ID for public URL / API use"),
  )

  class Meta:
    abstract = True

  def _generate_unique_public_id(self):
    """Try multiple times to avoid collisions."""
    for _ in range(10):
      pid = generate_public_id()
      if not self.__class__.objects.filter(token=pid).exists():
        return pid
    return generate_public_id(15)

  def save(self, *args, **kwargs):
    if not self.token:
      self.token = self._generate_unique_public_id()
    super().save(*args, **kwargs)
