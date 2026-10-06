from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import override


class UserLanguageMiddleware:
  """Activate the authenticated user's preferred language on every request.

  A user without a Preferences row (created on demand, e.g. on their first
  remembered choice) or without a language set keeps the normal detection
  (browser / site default). Only that missing row is caught - any other
  error surfaces instead of silently leaving the language unset."""

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    language = ''
    if request.user.is_authenticated:
      try:
        language = request.user.preferences.language
      except ObjectDoesNotExist:
        language = ''
    if not language:
      return self.get_response(request)
    # For this request only (override, not activate): a thread serves other
    # requests next, which must not inherit this user's language.
    with override(language):
      response = self.get_response(request)
      if hasattr(response, 'render') and not getattr(response, 'is_rendered', True):
        response.render()   # a lazy TemplateResponse: rendered in this language
      return response
