from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from cmnsd.models.mixins import TimestampMixin


class BasePreferences(TimestampMixin, models.Model):
  """
  Per-user preferences/settings, extending User via a OneToOne. Kept
  minimal on purpose - most preferences are project-specific (favorites,
  display options, etc.) and belong on the concrete Preferences model in
  each project's core app, not here. language is the one exception: it's
  read directly by cmnsd's own UserLanguageMiddleware via
  request.user.preferences, so it needs to exist under that name in any
  project using cmnsd - which is also why this is named Preferences and not
  Profile: "profile" more naturally describes account/identity info, not
  settings, and the class name and related_name should match, not mix.
  """
  user = models.OneToOneField(
    settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='preferences',
  )
  language = models.CharField(
    max_length=10, choices=settings.LANGUAGES, blank=True,
    help_text=_("Leave blank to fall back to browser/site default language detection"),
  )

  class Meta:
    abstract = True
    verbose_name = _("Preferences")
    verbose_name_plural = _("Preferences")

  def __str__(self) -> str:
    return f"{_('Preferences')}: {self.user}"
