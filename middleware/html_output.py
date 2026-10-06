from django.conf import settings


class HtmlOutputMiddleware:
  """
  Cleans up HTML output based on environment:
  - DEBUG=True, CMNSD_DEBUG_PRETTIFY=True  → pretty-print (consistent
    indentation, no blank lines) - opt-in only (see below), off by default.
  - DEBUG=True, CMNSD_DEBUG_PRETTIFY=False → pass through unchanged.
  - DEBUG=False                            → minify (whitespace stripped,
    smallest output).

  BeautifulSoup's prettify() inserts a newline before/after every tag with
  no concept of inline vs. block - it treats <mark> exactly like <div>. For
  HTML with an inline tag embedded mid-text (e.g. Al<mark>bert</mark>, from
  the |highlight filter), that newline collapses to a visible space in the
  browser, corrupting the actual rendered text: "Al bert" instead of
  "Albert" with "bert" highlighted. Confirmed empirically - not a fixable
  option/flag, it's how prettify() works. So it's opt-in via
  CMNSD_DEBUG_PRETTIFY (default False) for template-structure debugging
  sessions where that tradeoff is worth it, not the default dev behavior.
  minify_html (the DEBUG=False branch) doesn't have this problem - it's a
  real minifier, whitespace-aware for inline content.
  """

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    response = self.get_response(request)

    if getattr(response, 'streaming', False):
      return response

    if 'text/html' not in response.get('Content-Type', ''):
      return response

    if settings.DEBUG:
      if getattr(settings, 'CMNSD_DEBUG_PRETTIFY', False):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        response.content = soup.prettify().encode('utf-8')

    else:
      import minify_html
      response.content = minify_html.minify(
        response.content.decode('utf-8'),
        minify_js=True,
        minify_css=True,
      ).encode('utf-8')

    return response
