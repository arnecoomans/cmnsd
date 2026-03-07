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
  def filter_visibility(cls, queryset, request=None):
    if request and request.user.is_authenticated:
      user = request.user
      return queryset.filter(
      models.Q(visibility='p') |                                  # Public is always visible
      models.Q(visibility='c') |                                  # Community is visible to authenticated users
        models.Q(visibility='f', user=user) |                     # Family is visible to the owner
        models.Q(visibility='f', user__preferences__family=user) |# Family is visible to their family (reverse relation)
        models.Q(visibility='q', user=user)                       # Private is only visible to the owner
      )
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
  
  