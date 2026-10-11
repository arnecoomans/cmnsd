"""
Free-text matching for searches: "riede" finds Riedé and "riedé" finds
Riede. On PostgreSQL with django.contrib.postgres installed, both sides
go through UNACCENT() (the extension is created by cmnsd's migration
0002); anywhere else - SQLite in development - it's plain icontains, so
accents have to match there.

  from cmnsd.models.search import contains
  Q(**{contains('last_name'): term})
"""

from django.apps import apps
from django.db import connection


def ignores_accents():
  """Whether contains() lookups match regardless of accents here."""
  return connection.vendor == 'postgresql' and apps.is_installed('django.contrib.postgres')


def contains(path):
  """The case-insensitive 'contains' lookup for `path` (a field or a
  relation path), ignoring accents where the database can."""
  if ignores_accents():
    return f'{path}__unaccent__icontains'
  return f'{path}__icontains'
