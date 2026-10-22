from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

_FRACTION = [MinValueValidator(0.0), MaxValueValidator(1.0)]
# Rounding in a browser's arithmetic: x + w may come out a hair over 1.
_TOLERANCE = 1e-6


class RegionMixin(models.Model):
  """A region on an image: a box as fractions (0-1) of the image as shown -
  x and y its top left, w and h its size - so it survives a larger scan of
  the same image replacing the file. All four empty: no region. A point is
  a box without size (w = h = 0): "this spot".

  A box, not a circle: a radius as a fraction is a different length across
  and down on an image that isn't square, and everything else works with
  boxes - cropping, positioning on a page. Show it round if you like (an
  ellipse inside the box, CSS); store the box.

    class PersonOnPhoto(RegionMixin, models.Model): ...
    obj.region       # (x, y, w, h) or None
    obj.set_region((0.4, 0.1, 0.12, 0.18)); obj.set_region(None)

  clean() checks it: all four or none, and within the image."""

  region_x = models.FloatField(null=True, blank=True, validators=_FRACTION, verbose_name=_("region x"))
  region_y = models.FloatField(null=True, blank=True, validators=_FRACTION, verbose_name=_("region y"))
  region_w = models.FloatField(null=True, blank=True, validators=_FRACTION, verbose_name=_("region width"))
  region_h = models.FloatField(null=True, blank=True, validators=_FRACTION, verbose_name=_("region height"))

  class Meta:
    abstract = True

  @property
  def region(self):
    """(x, y, w, h) fractions, or None when it has none."""
    values = (self.region_x, self.region_y, self.region_w, self.region_h)
    return None if any(value is None for value in values) else values

  @property
  def has_region(self):
    return self.region is not None

  @property
  def region_is_point(self):
    region = self.region
    return region is not None and region[2] == 0 and region[3] == 0

  def set_region(self, box):
    """Set it from (x, y, w, h) - rounded to 4 decimals, a tenth of a
    permille - or clear it with None. Not saved."""
    if box is None:
      self.region_x = self.region_y = self.region_w = self.region_h = None
      return
    self.region_x, self.region_y, self.region_w, self.region_h = (round(float(value), 4) for value in box)

  def clean(self):
    super().clean()
    values = (self.region_x, self.region_y, self.region_w, self.region_h)
    if all(value is None for value in values):
      return
    if any(value is None for value in values):
      raise ValidationError(_("A region needs all four: x, y, width and height - or none."))
    x, y, w, h = values
    if min(values) < 0 or x + w > 1 + _TOLERANCE or y + h > 1 + _TOLERANCE:
      raise ValidationError(_("A region must lie within the image."))
