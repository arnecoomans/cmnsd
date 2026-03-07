from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError

import string, secrets
from inspect import getmembers, isfunction

# ================================================================
# Base Function:
# Generate public id (token)
# Creates a short, URL-safe token using letters and digits.
# ================================================================
def generate_public_id(length=10):
    """Generate a short, URL-safe public ID (not guessable)."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ================================================================
# BaseModel:
# Abstract base model with common fields and methods for all models.
# ================================================================

class BaseModel(models.Model):
  # Exposed as a class attribute so migrations referencing
  # cmnsd.models.BaseModel.generate_public_id resolve correctly
  # (cmnsd.models.BaseModel resolves to this class, not the module).
  generate_public_id = generate_public_id

  # ================================================================
  # BaseModel Fields:
  # ================================================================
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

  # ================================================================
  # Internal Methods
  # ================================================================
  def _generate_unique_public_id(self):
    """Try multiple times to avoid collisions."""
    for _ in range(10):
      pid = generate_public_id()
      if not self.__class__.objects.filter(token=pid).exists():
        return pid
    return generate_public_id(15)

  # ================================================================
  # Model Methods
  # ================================================================
  class Meta:
    abstract = True
  
  def save(self, *args, **kwargs):
    """Automatically assign a unique token if missing."""
    if not self.token:
      self.token = self._generate_unique_public_id()
    super().save(*args, **kwargs)
    
  def __str__(self):
    return getattr(self, 'name', f"{self.__class__.__name__} ({self.pk})")

  # ================================================================
  # Utility Methods: Ajax URL
  # ================================================================
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
  # ================================================================
  # Permissions and Access Control
  # ================================================================
  @property
  def disallow_access_fields(self):
    return ['id', 'slug', 'date_created', 'date_modified']

  # ================================================================
  # Class Methods for Querysets and Searchable Fields
  # ================================================================
  @classmethod
  def get_optimized_queryset(cls):
    """
    Return an optimized queryset for this model.
    Override in subclasses to add select_related, prefetch_related, annotations.
    Default: returns all objects.
    """
    return cls.objects.all()
  
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
  
  # ================================================================
  # Class Methods for Status Filtering
  # ================================================================
  @classmethod
  def filter_status(cls, queryset, request=None):
    if request and request.user.is_authenticated:
      if request.user.is_staff:
        # Staff can see Published, Concept, and Revoked
        return queryset.filter(models.Q(status='p') | models.Q(status='c') | models.Q(status='r'))
      else:
        # Authenticated non-staff can see Published and their own Concept
        return queryset.filter(models.Q(status='p') | models.Q(status='c', user=request.user))
    else:
      # Unauthenticated users can only see Published
      return queryset.filter(status='p')
