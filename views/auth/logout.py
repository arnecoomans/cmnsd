from django.contrib import messages
from django.contrib.auth.views import LogoutView
from django.utils.translation import gettext as _


class MessageLogoutView(LogoutView):
  def dispatch(self, request, *args, **kwargs):
    response = super().dispatch(request, *args, **kwargs)
    messages.success(request, _('You have been signed out.'))
    return response
