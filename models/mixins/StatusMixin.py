from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class StatusMixin(models.Model):
  """Adds a concept/published/revoked/deleted lifecycle status."""

  class Status(models.TextChoices):
    CONCEPT = 'c', _('Concept')
    PUBLISHED = 'p', _('Published')
    REVOKED = 'r', _('Revoked')
    DELETED = 'x', _('Deleted')

  status = models.CharField(
    max_length=1,
    choices=Status.choices,
    default=getattr(settings, 'CMNSD_DEFAULT_MODEL_STATUS', Status.PUBLISHED),
  )

  class Meta:
    abstract = True

  def is_status_visible_to(self, user=None):
    """filter_status() for one loaded object, in Python - for rendering
    decisions on objects that are already loaded (a relationship row, an
    avatar), where a query per object would be wasteful. Keep the two in
    step: published for everyone; concept for its creator and staff;
    revoked for staff; deleted for no one."""
    if self.status == self.Status.PUBLISHED:
      return True
    if not user or not user.is_authenticated:
      return False
    if self.status == self.Status.CONCEPT:
      return user.is_staff or self.user_id == user.pk
    if self.status == self.Status.REVOKED:
      return user.is_staff
    return False

  @property
  def needs_attention(self):
    """Not published yet (concept) or pulled back (revoked) - shown to the
    few who may see it, with a marking, so it gets resolved."""
    return self.status in (self.Status.CONCEPT, self.Status.REVOKED)

  @classmethod
  def filter_status(cls, queryset, request=None):
    # Request is required to determine user authentication and staff status for filtering.
    # If request is not provided, it will attempt to use cls.request if available.
    if not request and hasattr(cls, 'request'):
      request = cls.request
    if request and request.user.is_authenticated:
      if request.user.is_staff:
        # Staff can see Published, Concept, and Revoked
        return queryset.filter(models.Q(status='p') | models.Q(status='c') | models.Q(status='r'))
      # Authenticated non-staff can see Published and their own Concept
      return queryset.filter(models.Q(status='p') | models.Q(status='c', user=request.user))
    # Unauthenticated users can only see Published
    return queryset.filter(status='p')
