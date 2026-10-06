'''
  Search Decorators
  Marks a model method as searchable via SearchableMixin.get_searchable_fields(),
  so it can be discovered and used as a filter (e.g. by a FilterMixin).
  Usage:
    from cmnsd.decorators import searchable_function

    @searchable_function
    def is_visited(self):
        ...
'''


def searchable_function(func):
  """Marks a model method as searchable via SearchableMixin.get_searchable_fields()."""
  func.is_searchable = True
  return func
