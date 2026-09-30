import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _

MONTHS = [
  (1, _('january')), (2, _('february')), (3, _('march')), (4, _('april')),
  (5, _('may')), (6, _('june')), (7, _('july')), (8, _('august')),
  (9, _('september')), (10, _('october')), (11, _('november')), (12, _('december')),
]


class PartialDateMixin(models.Model):
  """
  Adds an optional, partially-specifiable date: year/month/day are each
  independently nullable, so a date can be recorded as just "1932", "March
  1932", or a full date - matching how genealogical/historical dates are
  often only partially known.

  date_qualifier says how sure the date is (after GEDCOM's ABT/BEF/AFT):
  exact, circa, before or after. Sorting still uses year/month/day as they
  are - "ca. 1950" sorts with 1950 - and only an exact, complete date has
  a weekday worth showing.
  """
  class DateQualifier(models.TextChoices):
    EXACT = 'exact', _('exact')
    CIRCA = 'circa', _('circa')
    BEFORE = 'before', _('before')
    AFTER = 'after', _('after')

  year = models.SmallIntegerField(null=True, blank=True)
  month = models.SmallIntegerField(null=True, blank=True, choices=MONTHS)
  day = models.SmallIntegerField(null=True, blank=True)
  date_qualifier = models.CharField(
    max_length=10, choices=DateQualifier.choices, default=DateQualifier.EXACT,
    help_text=_("How sure the date is"),
  )

  class Meta:
    abstract = True

  def is_exact_date(self):
    return self.date_qualifier == self.DateQualifier.EXACT

  def _qualifier_prefix(self):
    return {
      self.DateQualifier.CIRCA: _('ca.'),
      self.DateQualifier.BEFORE: _('before'),
      self.DateQualifier.AFTER: _('after'),
    }.get(self.date_qualifier)

  def year_display(self):
    """The year with its qualifier - 'ca. 1880', 'after 1918', '1943' -
    for places that show years only (a lifespan). '' when unknown."""
    if not self.year:
      return ''
    prefix = self._qualifier_prefix()
    return f"{prefix} {self.year}" if prefix else str(self.year)

  def partial_date_display(self):
    """'5-7-1968', '7-1968', '1968' - only the known parts - with the
    qualifier in front: 'ca. 1950', 'before 1950', 'after 1943'. '' when
    there's no year (a day without a month isn't shown either)."""
    if not self.year:
      return ''
    parts = [str(self.day)] if self.day and self.month else []
    if self.month:
      parts.append(str(self.month))
    text = '-'.join([*parts, str(self.year)])
    prefix = self._qualifier_prefix()
    return f"{prefix} {text}" if prefix else text

  def as_date(self):
    """Best-effort datetime.date, filling a missing month/day with 1. None if year is unknown."""
    if not self.year:
      return None
    return datetime.date(year=self.year, month=self.month or 1, day=self.day or 1)
