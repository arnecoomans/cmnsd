from django.db import models
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.utils.translation import gettext_lazy as _


class VisibilityMixin(models.Model):
  """Adds a public/community/family/private visibility level."""

  class Visibility(models.TextChoices):
    PUBLIC = 'p', _('Public')
    COMMUNITY = 'c', _('Community')
    FAMILY = 'f', _('Family')
    PRIVATE = 'q', _('Private')

  visibility = models.CharField(
    max_length=1,
    choices=Visibility.choices,
    default=getattr(settings, 'DEFAULT_MODEL_VISIBILITY', Visibility.COMMUNITY),
  )

  class Meta:
    abstract = True

  ''' Visibility Choices / Ordering '''
  @classmethod
  def get_visibility_choices(cls):
    return dict(cls.Visibility.choices)

  @classmethod
  def get_visibility_order_map(cls):
    return {
      'p': 3,
      'c': 2,
      'f': 1,
      'q': 0,
    }

  ''' Visibility Filtering (queryset) '''
  @classmethod
  def _lookup_path_exists(cls, model, path):
    """Return True if every step of a __ lookup path resolves on the given model."""
    current = model
    for part in path.split('__'):
      try:
        field = current._meta.get_field(part)
        current = getattr(field, 'related_model', None)
        if current is None:
          return False
      except FieldDoesNotExist:
        return False
    return True

  @classmethod
  def _family_lookup_path(cls, model):
    lookup = getattr(settings, 'CMNSD_VISIBILITY_FAMILY_LOOKUP_STORAGE', None)
    if lookup and cls._lookup_path_exists(model, lookup):
      return lookup
    return None

  @classmethod
  def filter_visibility(cls, queryset, request=None):
    if request and request.user.is_authenticated:
      user = request.user
      q = (
        models.Q(visibility='p') |
        models.Q(visibility='c') |
        models.Q(visibility='f', user=user) |
        models.Q(visibility='q', user=user)
      )
      family_lookup = cls._family_lookup_path(queryset.model)
      if family_lookup:
        q |= models.Q(visibility='f', **{family_lookup: user})
        # family_lookup joins to a (potentially to-many) relation - combined
        # with the other OR'd conditions that can duplicate matching rows.
        return queryset.filter(q).distinct()
      return queryset.filter(q)
    return queryset.filter(visibility='p')

  def _resolve_family_manager(self):
    lookup = type(self)._family_lookup_path(type(self))
    if not lookup:
      return None
    obj = self
    for part in lookup.split('__'):
      obj = getattr(obj, part, None)
      if obj is None:
        return None
    return obj

  ''' Visibility Checking (instance) '''
  def is_visible_to(self, user=None):
    """
    Check whether this object is visible to a given user without an extra
    queryset call. Mirrors filter_visibility() but evaluates in Python on
    the already-loaded instance. Use this in detail views.

    Args:
      user: A User instance or None (anonymous).

    Returns:
      bool: True if the user may see this object.
    """
    if self.visibility == 'p':
      return True

    if user is None or not user.is_authenticated:
      return False

    if self.visibility == 'c':
      return True

    if self.visibility == 'f':
      if self.user_id == user.pk:
        return True
      # Uses prefetch cache if the family lookup path was prefetched;
      # falls back to one query otherwise.
      manager = self._resolve_family_manager()
      if manager is None:
        return False
      return user in manager.all()

    if self.visibility == 'q':
      return self.user_id == user.pk

    return False

  @property
  def available_visibilities(self):
    return dict(self.Visibility.choices)

  ''' Visibility Helpers '''
  @property
  def is_private(self):
    return self.visibility == 'q'

  @property
  def is_family(self):
    return self.visibility == 'f'

  @property
  def is_community(self):
    return self.visibility == 'c'

  @property
  def is_public(self):
    return self.visibility == 'p'
