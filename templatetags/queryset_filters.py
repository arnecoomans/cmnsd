from django import template
from django.db.models import QuerySet
from django.db import models

register = template.Library()


@register.filter
def filter_by_status(queryset, request):
  """Delegate to the model's StatusMixin.filter_status - single source of truth."""
  return queryset.model.filter_status(queryset, request)


@register.filter
def filter_by_visibility(queryset, request):
  """Delegate to the model's VisibilityMixin.filter_visibility - single source of truth."""
  return queryset.model.filter_visibility(queryset, request)


@register.filter
def filter_by_user(queryset, user):
  """Restrict a queryset to objects owned by user, if authenticated."""
  if user.is_authenticated:
    queryset = queryset.filter(user=user)
  return queryset


@register.filter
def without(queryset, exclude_object):
  """Exclude objects from a queryset or list."""
  if isinstance(queryset, list):
    if isinstance(exclude_object, QuerySet):
      exclude_ids = set(exclude_object.values_list('id', flat=True))
      return [o for o in queryset if o.id not in exclude_ids]
    elif isinstance(exclude_object, models.Model):
      return [o for o in queryset if o.id != exclude_object.id]
    return queryset
  if isinstance(exclude_object, QuerySet):
    queryset = queryset.exclude(id__in=exclude_object.values_list('id', flat=True))
  elif isinstance(exclude_object, models.Model):
    queryset = queryset.exclude(id=exclude_object.id)
  return queryset


@register.filter
def match_queryset(queryset, include_object):
  """Restrict a queryset to objects matching include_object (a QuerySet or a single Model)."""
  if isinstance(include_object, QuerySet):
    queryset = queryset.filter(id__in=include_object.values_list('id', flat=True))
  elif isinstance(include_object, models.Model):
    queryset = queryset.filter(id=include_object.id)
  return queryset
