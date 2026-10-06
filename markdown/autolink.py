"""
Bare URLs in Markdown as links: "zie https://www.delpher.nl/..." links the
address, as people expect from text they typed. Python-Markdown only links
<https://...> (in angle brackets) and [text](url).

  CMNSD_MARKDOWN_EXTENSIONS = [..., 'cmnsd.markdown.autolink:AutolinkExtension']

Only http(s):// addresses. Trailing punctuation that ends a sentence
(".", ",", ")", ...) isn't part of the link. Not inside an existing link
(ANCESTOR_EXCLUDES) or code (Python-Markdown protects code spans and
blocks before inline patterns run). The HTML is still sanitized by the
|markdown filter (nh3), which also adds rel="noopener noreferrer".
"""

import xml.etree.ElementTree as etree

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor

# An http(s) address up to whitespace or a bracket; the last character
# isn't sentence punctuation.
BARE_URL = r'(?<![\w/"\'=])(https?://[^\s<>\[\]()]*[^\s<>\[\]().,;:!?\'"])'


class AutolinkProcessor(InlineProcessor):
  ANCESTOR_EXCLUDES = ('a',)

  def handleMatch(self, m, data):
    link = etree.Element('a')
    link.set('href', m.group(1))
    link.text = m.group(1)
    return link, m.start(0), m.end(0)


class AutolinkExtension(Extension):
  def extendMarkdown(self, md):
    # After the built-in links and autolinks (priority 120-160), before
    # emphasis: an underscore in a URL is part of the address.
    md.inlinePatterns.register(AutolinkProcessor(BARE_URL, md), 'cmnsd_bare_url', 100)
