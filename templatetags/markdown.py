import re

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.conf import settings

import markdown as md
import nh3

register = template.Library()

DEFAULT_MARKDOWN_EXTENSIONS = ['fenced_code', 'nl2br', 'tables']

# nh3's default allowlist has no entry for <code>'s class attribute, which
# fenced_code needs for its language-xxx class. Allow it, but only tokens
# matching language-xxx - anything else on the attribute is stripped so a
# language class can't be used to smuggle an arbitrary extra class in.
_SANITIZE_ATTRIBUTES = {**nh3.ALLOWED_ATTRIBUTES, 'code': {'class'}}
_LANGUAGE_CLASS_RE = re.compile(r'^language-[\w-]+$')


def _attribute_filter(tag, attr, value):
  if tag == 'code' and attr == 'class':
    kept = [c for c in value.split() if _LANGUAGE_CLASS_RE.match(c)]
    return ' '.join(kept) or None
  return value


@register.filter()
@stringfilter
def markdown(value):
  extensions = getattr(settings, 'CMNSD_MARKDOWN_EXTENSIONS', DEFAULT_MARKDOWN_EXTENSIONS)
  html = md.markdown(value, extensions=extensions)
  # python-markdown has no HTML sanitization of its own (safe_mode was
  # removed in 3.0) - raw <script>/event-handler HTML in the source passes
  # straight through otherwise, so this is the actual XSS boundary.
  clean = nh3.clean(html, attributes=_SANITIZE_ATTRIBUTES, attribute_filter=_attribute_filter)
  return mark_safe(clean)
