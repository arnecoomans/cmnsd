from django.db import models
from inspect import getmembers, isfunction


class SearchableMixin(models.Model):
  """No field footprint - safe to include on any model."""

  class Meta:
    abstract = True

  def __str__(self):
    return getattr(self, 'name', f"{self.__class__.__name__} ({self.pk})")

  @classmethod
  def get_optimized_queryset(cls):
    """
    Return an optimized queryset for this model.
    Override in subclasses to add select_related, prefetch_related, annotations.
    Default: returns all objects.
    """
    return cls.objects.all()

  @classmethod
  def get_model_fields(cls):
    return [f.name for f in cls._meta.get_fields()]

  @classmethod
  def get_searchable_fields(cls):
    """
    Return a combined list of real field names and @searchable_function methods.

    Returns:
      list[str]: All searchable field and function names.
    """
    fields = [f.name for f in cls._meta.get_fields()]
    functions = [
      name for name, func in getmembers(cls, predicate=isfunction)
      if getattr(func, "is_searchable", False)
    ]
    return fields + functions
