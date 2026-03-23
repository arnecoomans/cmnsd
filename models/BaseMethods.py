import functools

def ajax_login_required(func):
  """
  Marks a model method as requiring authentication when called via AJAX.
  Raises PermissionError if the method is called without an authenticated user.
  Expects self.request to be set on the model instance before calling.
  """
  @functools.wraps(func)
  def wrapper(self, *args, **kwargs):
    request = getattr(self, 'request', None)
    if not request or not request.user.is_authenticated:
      raise PermissionError("Authentication required.")
    return func(self, *args, **kwargs)
  wrapper.is_ajax_callable = True
  return wrapper

def ajax_function(func):
  """Marks a model method as callable via AJAX."""
  func.is_ajax_callable = True
  return func

def searchable_function(func):
  """Marks a model method as searchable."""
  func.is_searchable = True
  return func