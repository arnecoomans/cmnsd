def ajax_function(func):
  """Marks a model method as callable via AJAX."""
  func.is_ajax_callable = True
  return func