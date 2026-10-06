"""
Remembered UI state: which collapsible page sections (cmnsd/section.html)
are open, and which sort order a sortable list uses (e.g. a person
page's content: recently added / chronologically). Signed-in users only,
stored in the project's Preferences.ui_state (BasePreferences) and keyed
by section, not by page - closing "person.relationships" closes it on
every person page. The mechanism is generic; which keys and sort values
exist is the project's business. Saved by cmnsd.js (sections.js,
sort.js) through cmnsd/ui_urls.py.

Signed-out visitors always get the default: every section open and fully
rendered, nothing remembered (they only see a few public teaser pages,
and this sets no cookie for them).

Default: open, so everyone sees what's available at least once.
"""

import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

SECTION_KEY = re.compile(r'[a-z0-9_.-]{1,64}')
SORT_VALUE = re.compile(r'[a-z0-9_-]{1,32}')
MAX_SECTIONS = 50  # bounds what a client can make us store


def _preferences(user, create=False):
  """The user's Preferences row; created on demand when writing."""
  try:
    return user.preferences
  except ObjectDoesNotExist:
    if not create:
      return None
    # The project's concrete Preferences (a BasePreferences subclass),
    # found through the user's reverse relation - cmnsd never imports it.
    preferences_model = get_user_model().preferences.related.related_model
    return preferences_model.objects.get_or_create(user=user)[0]


def remembers_sections(request):
  """Whether sections are collapsible and remembered for this request -
  signed-in users only."""
  user = getattr(request, 'user', None)
  return bool(user and user.is_authenticated)


def is_section_open(request, key):
  if not remembers_sections(request):
    return True
  preferences = _preferences(request.user)
  sections = (preferences.ui_state or {}).get('sections', {}) if preferences else {}
  return bool(sections.get(key, True))


def set_section_open(request, key, is_open):
  """Remember one section's state for the signed-in user. Raises
  PermissionError when signed out, ValueError for a malformed key or too
  many stored sections."""
  if not remembers_sections(request):
    raise PermissionError("Only remembered for signed-in users.")
  if not SECTION_KEY.fullmatch(key or ''):
    raise ValueError("Invalid section key.")
  preferences = _preferences(request.user, create=True)
  sections = {**preferences.ui_state.get('sections', {}), key: bool(is_open)}
  if len(sections) > MAX_SECTIONS:
    raise ValueError("Too many sections.")
  preferences.ui_state = {**preferences.ui_state, 'sections': sections}
  preferences.save(update_fields=['ui_state'])


def get_sort(request, key, default, allowed):
  """The remembered sort order for `key` (e.g. 'person.content'), if it's
  one of `allowed`; otherwise `default`. Signed out: always `default`."""
  if not remembers_sections(request):
    return default
  preferences = _preferences(request.user)
  value = ((preferences.ui_state or {}).get('sorts', {}) if preferences else {}).get(key)
  return value if value in allowed else default


def set_sort(request, key, value):
  """Remember a sort order for the signed-in user. Raises PermissionError
  when signed out, ValueError for a malformed key or value or too many
  stored sorts. Which values mean something is up to the reader
  (get_sort's `allowed`)."""
  if not remembers_sections(request):
    raise PermissionError("Only remembered for signed-in users.")
  if not SECTION_KEY.fullmatch(key or '') or not SORT_VALUE.fullmatch(value or ''):
    raise ValueError("Invalid sort key or value.")
  preferences = _preferences(request.user, create=True)
  sorts = {**preferences.ui_state.get('sorts', {}), key: value}
  if len(sorts) > MAX_SECTIONS:
    raise ValueError("Too many sorts.")
  preferences.ui_state = {**preferences.ui_state, 'sorts': sorts}
  preferences.save(update_fields=['ui_state'])
