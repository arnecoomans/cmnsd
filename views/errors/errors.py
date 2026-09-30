from django.shortcuts import render
from django.conf import settings


def bad_request(request, exception):
  return render(request, 'errorpages/400.html', status=400)


def permission_denied(request, exception):
  context = {'login_url': getattr(settings, 'LOGIN_URL', '/accounts/login/')}
  return render(request, 'errorpages/403.html', context, status=403)


def page_not_found(request, exception):
  return render(request, 'errorpages/404.html', status=404)
