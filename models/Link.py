from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _
from urllib.parse import urlparse

from cmnsd.models import BaseModel

class BaseLink(BaseModel):
  url = models.URLField(
    max_length=500,
    help_text=_('URL of the link')
  )
  label = models.CharField(
    max_length=255,
    blank=True,
    help_text=_('Optional display label for the link')
  )
  
  class Meta:
    ordering = ['id']
    abstract = True
  
  def __str__(self):
    return self.label or self.display_name()
  
  def clean(self):
    """Validate URL."""
    super().clean()
    
    if self.url:
      validator = URLValidator()
      try:
        validator(self.url)
      except ValidationError:
        raise ValidationError({
          'url': _('Enter a valid URL.')
        })
  
  def display_name(self):
    """Return the domain name from the URL."""
    if self.label:
      return self.label
    try:
      parsed = urlparse(self.url)
      domain = parsed.netloc or parsed.path
      # Remove www. prefix if present
      if domain.startswith('www.'):
        domain = domain[4:]
      # Special Cases
      if domain.lower() in ['google.com', 'google.nl', 'google.co.uk']:
        search_query = parsed.query
        if 'q=' in search_query:
          query = search_query.split('q=')[1].split('&')[0]
          return f'{query} on Google'
      elif domain.lower() == 'blootkompas.nl':
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'locaties':
          location_name = path_parts[1].replace('-', ' ').title()
          return f'{location_name} on Blootkompas'
      elif domain.lower() in ['zoover.com', 'zoover.nl']:
        path_parts = parsed.path.strip('/').split('/')
        if path_parts[-1] in ['camping', 'hotel']:
          location_name = path_parts[-2].replace('-', ' ').title()
        else:
          location_name = path_parts[-1].replace('-', ' ').title()
        return f'{location_name} on Zoover'
      return domain
    except Exception:
      return self.url
  
  def save(self, *args, **kwargs):
    # Normalize URL protocol before validation
    if self.url and not self.url.startswith(('http://', 'https://')):
      self.url = f'https://{self.url}'
    
    self.full_clean()
    super().save(*args, **kwargs)