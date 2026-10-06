"""
External links in Markdown open in a new tab: every link with an absolute
http(s) address - [text](https://...), a bare https://... (markdown/autolink.py)
or <https://...> - gets target="_blank". A site's own links are relative
(/person/..., /content/...) and stay in the same tab.

  CMNSD_MARKDOWN_EXTENSIONS = [..., 'cmnsd.markdown.external_links:ExternalLinksExtension']

The |markdown filter's sanitizer (nh3) lets target="_blank" through - no
other value - and adds rel="noopener noreferrer" to every link.
"""

import re

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

EXTERNAL = re.compile(r'^https?://', re.IGNORECASE)


class ExternalLinksProcessor(Treeprocessor):
  def run(self, root):
    for link in root.iter('a'):
      if EXTERNAL.match(link.get('href', '')):
        link.set('target', '_blank')


class ExternalLinksExtension(Extension):
  def extendMarkdown(self, md):
    # After 'inline' (priority 20), where links - and autolinks - are made.
    md.treeprocessors.register(ExternalLinksProcessor(md), 'cmnsd_external_links', 5)
