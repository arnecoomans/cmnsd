from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import activate


class UserLanguageMiddleware:
  """Activate the authenticated user's preferred language on every request.

  A user without a Preferences row (created on demand, e.g. on their first
  remembered choice) or without a language set keeps the normal detection
  (browser / site default). Only that missing row is caught - any other
  error surfaces instead of silently leaving the language unset."""

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    if request.user.is_authenticated:
      try:
        language = request.user.preferences.language
      except ObjectDoesNotExist:
        language = ''
      if language:
        activate(language)
    return self.get_response(request)
