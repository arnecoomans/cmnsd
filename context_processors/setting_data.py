from django.conf import settings
from django.utils.translation import get_language


def setting_data(request):
  """Exposes select site-wide settings to every template, so views don't
  each have to pass SITE_NAME/META_DESCRIPTION themselves (e.g. for a base
  template's <title>/<meta> tags)."""
  return {
    'site_name': getattr(settings, 'SITE_NAME', ''),
    'meta_description': getattr(settings, 'META_DESCRIPTION', ''),

    # The language this page is in - the user's choice or the browser's -
    # not the setting: <html lang> tells screen readers and browsers.
    'language_code': get_language() or getattr(settings, 'LANGUAGE_CODE', 'en'),
    'charset': getattr(settings, 'DEFAULT_CHARSET', 'utf-8'),

    'load_on_ready': getattr(settings, 'CMNSD_LOAD_ON_READY', True),
    'search_character': getattr(settings, 'CMNSD_SEARCH_CHARACTER', 'q'),
  }
