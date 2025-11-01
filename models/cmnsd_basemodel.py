from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse

import string, secrets
from inspect import getmembers, isfunction

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
  """Abstract base model with a secure token and metadata fields."""

  token = models.CharField(
    max_length=20,
    unique=True,
    editable=False,
    blank=True,
    default=generate_public_id,
    help_text=_("Short unique ID for public URL use"),
  )

  status_choices = (
    ('c', _('Concept')),
    ('p', _('Published')),
    ('r', _('Revoked')),
    ('x', _('Deleted')),
  )
  status = models.CharField(
    max_length=1,
    choices=status_choices,
    default=getattr(settings, 'DEFAULT_MODEL_STATUS', 'p'),
  )

  date_created = models.DateTimeField(auto_now_add=True)
  date_modified = models.DateTimeField(auto_now=True)

  user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="%(class)s_created_by",
  )

  # ---------- Helpers ----------

  def _generate_unique_public_id(self):
    """Try multiple times to avoid collisions."""
    for _ in range(10):
      pid = generate_public_id()
      if not self.__class__.objects.filter(token=pid).exists():
        return pid
    return generate_public_id(15)

  def save(self, *args, **kwargs):
    """Automatically assign a unique token if missing."""
    if not self.token:
      self.token = self._generate_unique_public_id()
    super().save(*args, **kwargs)

  @property
  def ajax_slug(self):
    """Return a combined identifier for AJAX routes."""
    parts = [str(self.id)]
    if hasattr(self, 'slug') and self.slug:
      parts.append(self.slug)
    elif self.token:
      parts.append(self.token)
    return '-'.join(parts)

  @property
  def get_ajax_url(self):
    """Return the AJAX URL for the object."""
    return reverse(
      'cmnsd:dispatch_object_by_id_and_slug',
      args=[self.__class__.__name__.lower(), self.id, getattr(self, 'slug', self.token)],
    )

  @property
  def disallow_access_fields(self):
    return ['id', 'slug', 'date_created', 'date_modified']

  def __str__(self):
    return getattr(self, 'name', f"{self.__class__.__name__} ({self.pk})")

  @classmethod
  def get_model_fields(self):
    return [f.name for f in self._meta.get_fields()]
  
  @classmethod
  def get_searchable_fields(self):
    """
    Return a combined list of real field names and @searchable_function methods.

    This includes:
      - Model fields from _meta.get_fields()
      - Methods decorated with @searchable_function

    Returns:
      list[str]: All searchable field and function names.
    """
    fields = [f.name for f in self._meta.get_fields()]
    functions = [
      name for name, func in getmembers(self, predicate=isfunction)
      if getattr(func, "is_searchable", False)
    ]
    return fields + functions
  
  class Meta:
    abstract = True


class VisibilityModel(models.Model):
  visibility_choices      = (
      ('p', _('public')),
      ('c', _('commmunity')),
      ('f', _('family')),
      ('q', _('private')),
    )
  visibility = models.CharField(max_length=1, choices=visibility_choices, default=getattr(settings, 'DEFAULT_MODEL_VISIBILITY', 'c'))

  class Meta:
    abstract = True
  
  @property
  def get_visibility_choices(self):
    return dict(self.visibility_choices)

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