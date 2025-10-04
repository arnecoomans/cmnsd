from django import template
from django.utils import timezone
from django.utils.translation import pgettext
from django.utils.formats import date_format
from django.conf import settings
from datetime import datetime, date

register = template.Library()


@register.filter
def humanize_date(value, fmt=None):
  """
  Convert a date or datetime into a human-readable string.

  Behavior:
    - If the date is within HUMANIZE_DATE_MAX_DAYS (default: 365 days)
      → returns a relative expression like "3 days ago" or "in 2 weeks".
    - Otherwise → formats the date using Django settings or a provided format.

  Translation:
    Uses gettext/pgettext for contextual translations (e.g. "in 2 days", "2 days ago").

  Usage:
      {{ mydate|humanize_date }}
      {{ mydate|humanize_date:"j F Y" }}

  Configurable via settings.py:
      HUMANIZE_DATE_MAX_DAYS = 365
      HUMANIZE_DATE_FORMAT = "l j F Y H:i"
  """
  if not value:
    return ""

  # --- Load config values ---
  max_days = getattr(settings, "HUMANIZE_DATE_MAX_DAYS", 365)
  default_fmt = getattr(settings, "HUMANIZE_DATE_FORMAT", "l j F Y H:i")
  fmt = fmt or default_fmt

  # --- Normalize date/time ---
  now = timezone.now()
  if isinstance(value, date) and not isinstance(value, datetime):
    value = datetime(value.year, value.month, value.day, tzinfo=timezone.get_current_timezone())
  elif timezone.is_naive(value):
    value = timezone.make_aware(value, timezone.get_current_timezone())

  delta = value - now
  days = delta.days
  seconds = delta.seconds
  abs_days = abs(days)
  abs_seconds = abs(seconds)

  # --- Within range: return humanized relative time ---
  if abs_days < max_days:
    # Determine unit and count
    if abs_days == 0:
      hours = abs_seconds // 3600
      minutes = (abs_seconds % 3600) // 60
      if hours:
        text = pgettext("time difference", "%(count)d hour") % {"count": hours} if hours == 1 else \
               pgettext("time difference", "%(count)d hours") % {"count": hours}
      elif minutes:
        text = pgettext("time difference", "%(count)d minute") % {"count": minutes} if minutes == 1 else \
               pgettext("time difference", "%(count)d minutes") % {"count": minutes}
      else:
        return pgettext("time difference", "just now")
    elif abs_days < 7:
      text = pgettext("time difference", "%(count)d day") % {"count": abs_days} if abs_days == 1 else \
             pgettext("time difference", "%(count)d days") % {"count": abs_days}
    elif abs_days < 30:
      weeks = abs_days // 7
      text = pgettext("time difference", "%(count)d week") % {"count": weeks} if weeks == 1 else \
             pgettext("time difference", "%(count)d weeks") % {"count": weeks}
    else:
      months = abs_days // 30
      text = pgettext("time difference", "%(count)d month") % {"count": months} if months == 1 else \
             pgettext("time difference", "%(count)d months") % {"count": months}

    if days > 0:
      return pgettext("time difference future", "in %(text)s") % {"text": text}
    else:
      return pgettext("time difference past", "%(text)s ago") % {"text": text}

  # --- Older or far-future date: return formatted date ---
  local_value = timezone.localtime(value)
  # Use Django's locale-aware date_format (instead of strftime)
  return date_format(local_value, fmt, use_l10n=True)
