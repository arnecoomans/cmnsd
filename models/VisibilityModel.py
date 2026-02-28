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

  ''' Visibility Helpers '''
  @property
  def is_private(self):
    print(f"Checking if visibility '{self.visibility}' is private")
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