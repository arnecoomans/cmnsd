from django.shortcuts import render
from django.conf import settings


def bad_request(request, exception):
  return render(request, 'errorpages/400.html', status=400)


def permission_denied(request, exception):
  context = {'login_url': getattr(settings, 'LOGIN_URL', '/accounts/login/')}
  return render(request, 'errorpages/403.html', context, status=403)


def page_not_found(request, exception):
  return render(request, 'errorpages/404.html', status=404)


def server_error(request):
  """handler500: a page that works when the rest doesn't - rendered without
  the request's context (the context processors look up the user, which
  needs the database: maybe what just failed), from a standalone template
  (errorpages/base_error.html: inline CSS, no static files), and plain text
  if even that fails."""
  from django.http import HttpResponseServerError
  from django.template import loader
  try:
    html = loader.get_template('errorpages/500.html').render({'site_name': getattr(settings, 'SITE_NAME', '')})
  except Exception:   # the last resort: nothing else may raise here
    html = '<!doctype html><title>Server error</title><h1>Server error (500)</h1>'
  return HttpResponseServerError(html)

