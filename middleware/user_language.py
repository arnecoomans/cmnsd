from django.utils.translation import activate


class UserLanguageMiddleware:
  """Activate the authenticated user's preferred language on every request."""

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    if request.user.is_authenticated:
      try:
        lang = request.user.preferences.language
        if lang:
          activate(lang)
      except Exception:
        pass
    return self.get_response(request)
