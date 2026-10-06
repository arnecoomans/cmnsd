import string
import unicodedata

from django import template

register = template.Library()

_OTHER = '#'


def _initial(value):
  """First letter of value as A-Z, accents stripped (É -> E); anything
  else, or a blank value, groups under '#'."""
  value = (value or '').strip()
  if not value:
    return _OTHER
  letter = unicodedata.normalize('NFKD', value[0]).encode('ascii', 'ignore').decode().upper()
  return letter if letter in string.ascii_uppercase else _OTHER


@register.filter
def group_by_initial(objects, field):
  """{% with index=person_list|group_by_initial:'last_name' %} - groups
  objects under the first letter of `field`, for an A-Z list.

  Returns {'letters': [...], 'groups': [...]}:
    letters: every letter A-Z plus '#', each {'letter', 'anchor', 'count'}
             - the full alphabet, so an index doesn't shift when a letter
             has no entries (count 0, rendered muted).
    groups:  only the non-empty ones, in the same order, each
             {'letter', 'anchor', 'items'}.
  `anchor` is safe for an HTML id/fragment ('#' becomes 'other').

  Items within a group are sorted case-insensitively on `field`; the
  sort is stable, so the incoming order (e.g. by given name) is kept
  among equal values. Case-insensitive because the database's ordering
  may not be - SQLite sorts 'van Dijk' after 'Visser'."""
  buckets = {}
  for obj in objects:
    buckets.setdefault(_initial(getattr(obj, field, '')), []).append(obj)

  letters, groups = [], []
  for letter in [*string.ascii_uppercase, _OTHER]:
    items = buckets.get(letter, [])
    anchor = 'other' if letter == _OTHER else letter
    letters.append({'letter': letter, 'anchor': anchor, 'count': len(items)})
    if items:
      items = sorted(items, key=lambda obj: (getattr(obj, field, '') or '').casefold())
      groups.append({'letter': letter, 'anchor': anchor, 'items': items})
  return {'letters': letters, 'groups': groups}
