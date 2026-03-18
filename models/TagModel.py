from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from django.urls import reverse_lazy

from .BaseModel import BaseModel

class TagModel(BaseModel):
  slug                = models.CharField(max_length=64, unique=True, help_text=f"{ _('Identifier in URL') } ({ _('automatically generated') })")
  name                = models.CharField(max_length=128, help_text=_('Name of tag'))
  parent              = models.ForeignKey("self", on_delete=models.CASCADE, related_name='children', null=True, blank=True)
  description         = models.TextField(blank=True, help_text=_('description of this tag, why it is relevant').capitalize())

  class Meta:
    abstract = True
    constraints = [
      models.UniqueConstraint(fields=['parent', 'name'], name='unique_name_per_parent')
    ]

  def __str__(self) -> str:
    return self.display_name()
    
  def save(self, *args, **kwargs):
    if not self.name and self.slug:
      self.name = self.slug.replace('-', ' ').replace('_', ' ').replace('+', ' ').title()
    if not self.slug and self.name:
      self.slug = slugify(self.name)
    super().save(*args, **kwargs)

  def display_name(self) -> str:
    name = ''
    if self.parent:
      name += self.parent.name + ': '
    name += self.name
    return name
  
  def clean(self):
    """Validate name uniqueness within parent scope."""
    super().clean()
    qs = self.__class__.objects.filter(
      name=self.name,
      parent=self.parent,
    )
    if self.pk:
      qs = qs.exclude(pk=self.pk)
    if qs.exists():
      raise ValidationError({
        'name': _('A tag with this name already exists under the same parent.')
      })