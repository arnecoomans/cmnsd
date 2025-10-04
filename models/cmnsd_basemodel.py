from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse

import string, secrets
if 'django.contrib.sites' in settings.INSTALLED_APPS:
  from django.contrib.sites.models import Site
  from django.contrib.sites.managers import CurrentSiteManager


''' Base functions '''
def generate_public_id(length=10):
    """Generate a short, URL-safe public ID (not guessable)."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

''' BaseModel
    Abstract base model with common fields and methods
    for all models in the project.
'''
class BaseModel(models.Model):
  token = models.CharField(
    max_length=20,
    unique=True,
    editable=False,
    default=generate_public_id,
    help_text="Short unique ID for public URL use"
  )
  
  status_choices = (
    ('c', _('concept').capitalize()),
    ('p', _('published').capitalize()),
    ('r', _('revoked').capitalize()),
    ('x', _('deleted').capitalize()),
  )
  status = models.CharField(max_length=1, choices=status_choices, default='p')

  date_created = models.DateTimeField(auto_now_add=True)
  date_modified = models.DateTimeField(auto_now=True)
  user = models.ForeignKey(
    get_user_model(),
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="%(class)s_created_by"
  )

  ''' Easy Access '''
  @property
  def ajax_slug(self):
    """ Return a slug for the object, combining ID and slug if available. """
    parts = [str(self.id)]
    if hasattr(self, 'slug'):
      parts.append(str(self.slug))
    elif hasattr(self, 'token'):
      parts.append(str(self.token))
    return '-'.join(parts)

  @property
  def get_ajax_url(self):
    """ Return the AJAX URL for the object, if defined. """
    return reverse('cmnsd:dispatch_object_by_id_and_slug', args=[self.__class__.__name__.lower(), self.id, getattr(self, 'slug', self.token)])
    return None
  
  ''' Configuration values 
      Can be overridden or appended in subclasses using:
      def function_name(self):
        return super().function_name + ['appending value']
  '''
  @property
  def disallow_access_fields(self):
    return ['id', 'slug', 'date_created', 'date_modified']
  

  class Meta:
    ''' Avoid creating a database table for this model '''
    abstract = True

  def __str__(self):
    if hasattr(self, "name"):
      return self.name
    return f"{self.__class__.__name__} object ({self.pk})"

  def get_model_fields(self):
    return [field.name for field in self._meta.get_fields()]


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