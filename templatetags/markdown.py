import re

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.conf import settings

import markdown as md
import nh3

register = template.Library()

# cmnsd_autolink: bare http(s):// addresses become links (cmnsd/markdown/autolink.py);
# cmnsd_external_links: links to other sites open in a new tab
# (cmnsd/markdown/external_links.py).
DEFAULT_MARKDOWN_EXTENSIONS = [
  'fenced_code', 'nl2br', 'tables',
  'cmnsd.markdown.autolink:AutolinkExtension', 'cmnsd.markdown.external_links:ExternalLinksExtension',
]

# nh3's default allowlist has no entry for <code>'s class attribute, which
# fenced_code needs for its language-xxx class. Allow it, but only tokens
# matching language-xxx - anything else on the attribute is stripped so a
# language class can't be used to smuggle an arbitrary extra class in.
_SANITIZE_ATTRIBUTES = {
  **nh3.ALLOWED_ATTRIBUTES, 'code': {'class'},
  # target="_blank" on external links (cmnsd/markdown/external_links.py) - nothing
  # else as a target (_attribute_filter).
  'a': {*nh3.ALLOWED_ATTRIBUTES.get('a', set()), 'target', 'class'},
  # A mention (cmnsd/markdown/mentions.py): its class, nothing else.
  'span': {*nh3.ALLOWED_ATTRIBUTES.get('span', set()), 'class'},
}
_LANGUAGE_CLASS_RE = re.compile(r'^language-[\w-]+$')
_MENTION_CLASSES = {'mention', 'mention--hidden'}


def _attribute_filter(tag, attr, value):
  if tag == 'a' and attr == 'target':
    return value if value == '_blank' else None
  if tag in ('a', 'span') and attr == 'class':
    kept = [c for c in value.split() if c in _MENTION_CLASSES]
    return ' '.join(kept) or None
  if tag == 'code' and attr == 'class':
    kept = [c for c in value.split() if _LANGUAGE_CLASS_RE.match(c)]
    return ' '.join(kept) or None
  return value


@register.simple_tag
def mentions_attrs():
  """<textarea ... {% mentions_attrs %}> - a hand-written textarea that
  offers mentions while typing (cmnsd.js mentions.js), as MentionTextarea
  does for a form field."""
  from django.utils.html import format_html_join
  from cmnsd.markdown.mentions import mention_field_attrs
  return format_html_join(' ', '{}="{}"', mention_field_attrs().items())


# A faithful text - a transcript of a document: Markdown only for what the
# original has and the reader needs (paragraphs, line breaks, headings,
# tables, bold and italic, mentions), nothing that changes or swallows
# characters. Bold and italic by a strict rule (_FaithfulEmphasis): the
# asterisks hug their words - **PASSAGIERS**, *Sumatra* - so a footnote
# asterisk after a word ("echtg.*; J. Hagen*") stays one; \* is an
# asterisk. Off: lists (a register's "0. J. F. Bruins" isn't renumbered),
# underscores, code (OCR noise stays), quotes, rules and setext headings
# ("---" under a line), link
# definitions ("[1]: ..." isn't swallowed), and raw HTML: a "<" in a
# transcript is a character of the original (or OCR noise), shown as such -
# not a tag the sanitizer would remove, its words with it.
_FAITHFUL_OFF_PRE = ('html_block',)
_FAITHFUL_OFF_BLOCKS = ('olist', 'ulist', 'code', 'quote', 'hr', 'setextheader', 'reference')
_FAITHFUL_OFF_INLINE = ('em_strong', 'em_strong2', 'not_strong', 'backtick', 'html')

# Opening: not right after a word or asterisk, right before a letter or
# digit; closing: right after a non-space, not right before a word or
# asterisk. The text between them is still Markdown (a mention in bold).
# \x02: the placeholder python-markdown puts where a link already is - a
# mention in bold.
_FAITHFUL_STRONG = r'(?<![\w*\\])(\*\*)(?=[^\W_]|\x02)([^*\n]+?)(?<=\S)\*\*(?![\w*])'
_FAITHFUL_EM = r'(?<![\w*\\])(\*)(?=[^\W_]|\x02)([^*\n]+?)(?<=\S)\*(?![\w*])'


def escape_faithful_markdown(text):
  """Text that wasn't written as Markdown - OCR, a fetched text - with a
  backslash before exactly what the faithful rendering would read as
  Markdown: a "#" starting a line (a heading) and the asterisks of would-be
  bold or italic (_FAITHFUL_STRONG / _FAITHFUL_EM). Other asterisks (a
  footnote mark after a word) are left alone - they're safe already, and a
  checker isn't faced with backslashes everywhere. Where the original
  really has a heading or bold, the checker takes the backslash away: a
  choice by hand - all Markdown in a transcript is typed."""
  escape = lambda delimiter: lambda m: '\\*' * len(delimiter) + m.group(2) + '\\*' * len(delimiter)
  text = re.sub(r'(?m)^(\s{0,3})#', r'\1\\#', text or '')
  text = re.sub(_FAITHFUL_STRONG, escape('**'), text)
  return re.sub(_FAITHFUL_EM, escape('*'), text)


def render_markdown(value, request=None, faithful=False):
  """Markdown as safe HTML - the |markdown and |markdown_faithful filters.
  With the request, mentions ([Eric](person:<token>), cmnsd/markdown/
  mentions.py) link to what this viewer may see; without it nothing is
  visible - mentions stay text, a person's name obfuscated: fail closed."""
  from cmnsd.markdown.mentions import MentionExtension
  extensions = [*getattr(settings, 'CMNSD_MARKDOWN_EXTENSIONS', DEFAULT_MARKDOWN_EXTENSIONS), MentionExtension(request=request)]
  if faithful:
    extensions = [e for e in extensions if e != 'fenced_code']
  converter = md.Markdown(extensions=extensions)
  if faithful:
    for name in _FAITHFUL_OFF_PRE:
      if name in converter.preprocessors:
        converter.preprocessors.deregister(name)
    for name in _FAITHFUL_OFF_BLOCKS:
      if name in converter.parser.blockprocessors:
        converter.parser.blockprocessors.deregister(name)
    for name in _FAITHFUL_OFF_INLINE:
      if name in converter.inlinePatterns:
        converter.inlinePatterns.deregister(name)
    from markdown.inlinepatterns import SimpleTagInlineProcessor
    # Where em_strong was (50): after links, so a mention can be in bold.
    converter.inlinePatterns.register(SimpleTagInlineProcessor(_FAITHFUL_STRONG, 'strong'), 'faithful_strong', 51)
    converter.inlinePatterns.register(SimpleTagInlineProcessor(_FAITHFUL_EM, 'em'), 'faithful_em', 50)
  html = converter.convert(str(value))
  # python-markdown has no HTML sanitization of its own (safe_mode was
  # removed in 3.0) - raw <script>/event-handler HTML in the source passes
  # straight through otherwise, so this is the actual XSS boundary.
  clean = nh3.clean(html, attributes=_SANITIZE_ATTRIBUTES, attribute_filter=_attribute_filter)
  return mark_safe(clean)


@register.filter()
@stringfilter
def markdown(value, request=None):
  """{{ text|markdown:request }} - Markdown as safe HTML, with mentions for
  what this viewer may see (render_markdown)."""
  return render_markdown(value, request)


@register.filter()
@stringfilter
def markdown_faithful(value, request=None):
  """{{ transcript.text|markdown_faithful:request }} - a text that must stay
  as written (a transcript): paragraphs, line breaks, headings, tables and
  mentions only - no lists, emphasis or escapes that would change it
  (_FAITHFUL_OFF_*)."""
  return render_markdown(value, request, faithful=True)
