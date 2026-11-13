import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from cmnsd import login_links, login_throttle

logger = logging.getLogger(__name__)


class RedirectAuthenticatedLoginView(LoginView):
  template_name = 'auth/login.html'

  def dispatch(self, request, *args, **kwargs):
    if request.user.is_authenticated:
      messages.info(request, _('You are already signed in.'))
      return redirect(getattr(settings, 'LOGIN_REDIRECT_URL', '/'))
    return super().dispatch(request, *args, **kwargs)

  def get_context_data(self, **kwargs):
    # "Mail me a login link" next to the password (CMNSD_LOGIN_LINKS).
    return {**super().get_context_data(**kwargs), 'login_links': login_links.enabled()}

  def form_valid(self, form):
    response = super().form_valid(form)
    messages.success(self.request, _('You have been signed in.'))
    logger.info(f"Login success: {form.get_user()} from {login_throttle.client_ip(self.request)}")
    return response

  def form_invalid(self, form):
    logger.warning(f"Login failure: {form.data.get('username')} from {login_throttle.client_ip(self.request)}")
    if getattr(self.request, 'login_throttled', False):
      # Too many guesses (cmnsd/login_throttle.py): said, not only "wrong
      # password" - and the way in that stays open.
      message = _("Too many attempts to sign in. Try again in a while.")
      if login_links.enabled():
        message = f"{message} {_('Or mail yourself a login link.')}"
      messages.error(self.request, message)
    return super().form_invalid(form)
