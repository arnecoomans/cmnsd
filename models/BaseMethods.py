def ajax_function(func):
  """Marks a model method as callable via AJAX."""
  func.is_ajax_callable = True
  return func

def searchable_function(func):
  """Marks a model method as searchable."""
  func.is_searchable = True
  return func