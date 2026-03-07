from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.utils.translation import gettext as _


class RedirectAuthenticatedLoginView(LoginView):
  def dispatch(self, request, *args, **kwargs):
    if request.user.is_authenticated:
      messages.info(request, _('You are already signed in.'))
      return redirect(getattr(settings, 'LOGIN_REDIRECT_URL', '/'))
    return super().dispatch(request, *args, **kwargs)

  def form_valid(self, form):
    response = super().form_valid(form)
    messages.success(self.request, _('You have been signed in.'))
    return response
