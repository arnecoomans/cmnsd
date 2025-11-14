from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy as __
from django.utils.text import slugify

from django.urls import reverse_lazy

from django.contrib.auth.models import User

from .cmnsd_basemodel import BaseModel, VisibilityModel

''' Category model
'''
class Category(BaseModel):
  slug                = models.CharField(max_length=255, unique=True, help_text=f"{ _('Identifier in URL') } ({ _('automatically generated') })")
  name                = models.CharField(max_length=255, help_text=_('Name of category'))
  parent              = models.ForeignKey("self", on_delete=models.CASCADE, related_name='children', null=True, blank=True)

  class Meta:
    abstract = True
    verbose_name_plural = 'categories'
    ordering = ['parent__name', 'name']

  def __str__(self) -> str:
    if self.parent:
      return f"{ self.parent.name }: { self.name }"
    return self.name
  
  def save(self, *args, **kwargs):
    # Handle Parent Identifiers
    if ':' in self.name:
      parent_name, name = [part.strip() for part in self.name.split(':', 1)]
      parent_category, created = self.__class__.objects.get_or_create(name=parent_name)
      self.parent = parent_category
      self.name = name
    # Auto-generate slug from name if not provided
    if not self.slug:
      self.slug = slugify(self.name)
    super().save(*args, **kwargs)

  js_template_name = 'categories'
