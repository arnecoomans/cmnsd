"""
Login links: a link, sent by mail, that logs its user in once - instead of
a password. Sent by staff (an invite: "come and look") or asked for on the
login page (a request: "mail me a link"). Logic in cmnsd/login_links.py.

Stored, not a stateless token, so one link can be revoked before it's
used, a new one can replace the open ones, and who invited whom stays
visible. Only a hash of the token is kept: the token itself is only ever
in the mail - a copy of the database opens nothing.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class LoginLinkQuerySet(models.QuerySet):
  def open(self):
    """Not used, not revoked, not expired - whether the account may log in
    is checked when it's used (LoginLink.is_valid)."""
    return self.filter(used_at=None, revoked_at=None, expires_at__gt=timezone.now())


class LoginLink(models.Model):
  class Purpose(models.TextChoices):
    INVITE = 'invite', _("invite")      # sent by staff
    REQUEST = 'request', _("request")   # asked for on the login page

  user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='login_links')
  token_hash = models.CharField(max_length=64, unique=True)
  purpose = models.CharField(max_length=10, choices=Purpose.choices)
  created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
  created_at = models.DateTimeField(auto_now_add=True)
  expires_at = models.DateTimeField()
  # Where the link lands after logging in - an internal path only (checked when it's made and used).
  next = models.CharField(max_length=500, blank=True)
  used_at = models.DateTimeField(null=True, blank=True)
  revoked_at = models.DateTimeField(null=True, blank=True)
  revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

  objects = LoginLinkQuerySet.as_manager()

  class Meta:
    ordering = ['-created_at']
    verbose_name = _("login link")
    verbose_name_plural = _("login links")

  def __str__(self):
    return f"{self.get_purpose_display()} for {self.user} ({self.created_at:%Y-%m-%d %H:%M})"

  @property
  def state(self):
    """'used', 'revoked', 'expired' or 'open' - the link's own state; '' for
    one not made yet (an admin inline's empty row)."""
    if self.expires_at is None:
      return ''
    if self.used_at:
      return 'used'
    if self.revoked_at:
      return 'revoked'
    if self.expires_at <= timezone.now():
      return 'expired'
    return 'open'

  def get_state_display(self):
    return {'used': _("used"), 'revoked': _("revoked"), 'expired': _("expired"), 'open': _("open"), '': ''}[self.state]

  def is_valid(self):
    """Open, and its account may log in (active - not waiting for approval)."""
    return self.state == 'open' and self.user.is_active
