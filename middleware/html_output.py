from django.conf import settings


class HtmlOutputMiddleware:
  """
  Cleans up HTML output based on environment:
  - DEBUG=True  → pretty-print (consistent indentation, no blank lines)
  - DEBUG=False → minify (whitespace stripped, smallest output)
  """

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    response = self.get_response(request)

    if 'text/html' not in response.get('Content-Type', ''):
      return response

    if settings.DEBUG:
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
