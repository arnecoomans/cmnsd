from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .BaseModel import BaseModel

if 'django.contrib.sites' in settings.INSTALLED_APPS:
  from django.contrib.sites.models import Site
  from django.contrib.sites.managers import CurrentSiteManager

# Only allow option for MultiSiteBaseModel if 'django.contrib.sites' is available
if 'django.contrib.sites' in settings.INSTALLED_APPS:
  ''' MultiSiteBaseModel 
      Extends BaseModel with multi-site support.
  '''
  class MultiSiteBaseModel(BaseModel):
    """Abstract base model with common fields and methods."""
    sites = models.ManyToManyField(Site, related_name="%(class)s_sites")
    objects = models.Manager()  # Default manager
    on_site = CurrentSiteManager()  # Site-specific manager

    class Meta:
      abstract = True

    def count_sites(self):
      return self.sites.count()
    count_sites.short_description = _('sites')