from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

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
  
  @classmethod
  def get_visibility_choices(self):
    return dict(self.visibility_choices)
  @classmethod
  def get_visibility_order_map(self):
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
    from django.core.exceptions import FieldDoesNotExist
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
  def filter_visibility(cls, queryset, request=None):
    if request and request.user.is_authenticated:
      user = request.user
      q = (
        models.Q(visibility='p') |
        models.Q(visibility='c') |
        models.Q(visibility='f', user=user) |
        models.Q(visibility='q', user=user)
      )
      family_lookup = getattr(settings, 'VISIBILITY_FAMILY_LOOKUP', 'user__preferences__family')
      if family_lookup and cls._lookup_path_exists(queryset.model, family_lookup):
        q |= models.Q(visibility='f', **{family_lookup: user})
      return queryset.filter(q)
    else:
      return queryset.filter(visibility='p')

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
      # Uses prefetch cache if user__preferences__family was prefetched;
      # falls back to one query otherwise.
      return user in self.user.preferences.family.all()

    if self.visibility == 'q':
      return self.user_id == user.pk

    return False

  @property
  def available_visibilities(self):
    return dict(self.visibility_choices)

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
  
  