from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from cmnsd.models.BaseModel import BaseModel
from cmnsd.models.VisibilityModel import VisibilityModel


class PageModel(BaseModel, VisibilityModel):
  """Abstract base for static content pages.

  Concrete subclasses provide the table and URL resolution.
  Inherits status, token, user, date_created, date_modified from BaseModel.
  Inherits visibility from VisibilityModel.

  Each (slug, language) pair is unique — one row per page per language.
  The view falls back to LANGUAGE_CODE if no translation exists.
  """

  slug = models.SlugField(help_text=_('URL identifier, e.g. "privacy" or "about"'))
  language = models.CharField(
    max_length=10,
    choices=settings.LANGUAGES,
    default=settings.LANGUAGE_CODE,
    help_text=_('Language this page is written in'),
  )
  title = models.CharField(max_length=200)
  body = models.TextField(blank=True, help_text=_('Markdown supported'))

  class Meta:
    abstract = True
    ordering = ['slug', 'language']
    unique_together = [('slug', 'language')]

  def __str__(self):
    return f'{self.title} ({self.language})'
