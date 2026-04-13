import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class RedirectAuthenticatedLoginView(LoginView):
  def dispatch(self, request, *args, **kwargs):
    if request.user.is_authenticated:
      messages.info(request, _('You are already signed in.'))
      return redirect(getattr(settings, 'LOGIN_REDIRECT_URL', '/'))
    return super().dispatch(request, *args, **kwargs)

  def form_valid(self, form):
    response = super().form_valid(form)
    messages.success(self.request, _('You have been signed in.'))
    logger.info(f"Login success: {form.get_user()} from {self.request.META.get('REMOTE_ADDR')}")
    return response

  def form_invalid(self, form):
    logger.warning(f"Login failure: {form.data.get('username')} from {self.request.META.get('REMOTE_ADDR')}")
    return super().form_invalid(form)
