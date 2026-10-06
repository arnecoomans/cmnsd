from django.conf import settings


def default_language():
  """The site's language as a short code ('en' for LANGUAGE_CODE 'en-us'),
  matching the LANGUAGES choices - e.g. a Page's default language."""
  return settings.LANGUAGE_CODE.split('-')[0]
