"""
Login links (cmnsd.models.LoginLink): a mailed link that logs its user in
once, instead of a password.

- An invite: staff send it (send_login_link view, the admin's user action)
  - valid CMNSD_LOGIN_LINK_INVITE_MAX_AGE (7 days), with an optional
  message and a page to land on. Sending again revokes the open invites.
- A request: "mail me a login link" on the login page - valid
  CMNSD_LOGIN_LINK_REQUEST_MAX_AGE (15 minutes), at most
  CMNSD_LOGIN_LINK_REQUESTS_PER_HOUR per account. A new one revokes the
  earlier open requests.

The token (secrets.token_urlsafe) is only in the mail; the database has
its SHA-256 hash. The link opens a page with a button and only that POST
logs in (views/auth/login_link.py): mail scanners that open every link
don't use it up. Only an active account (not waiting for approval) logs
in. Staff accounts too, from anyone who may send: whoever reads their
mail can reset their password already - a login link adds no way in. And
to yourself: signing in on another device.

- A copied link: a superuser makes an invite without a mail, to pass on
  themselves - a chat, a text (copy_login_link view). Superusers only:
  whoever holds the link can sign in as that user, and a superuser may do
  anything already. No address needed. It's an invite like any other -
  same age, and it replaces the open one.

Every send, copy, revoke and use is logged on the user (admin history) - never
the token.

Off unless the project turns it on: CMNSD_LOGIN_LINKS = True (fmly: from
.env). Off, its pages are 404 and nothing offers it; the table stays
empty.
"""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import login
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from cmnsd.models.LoginLink import LoginLink

BACKEND = 'django.contrib.auth.backends.ModelBackend'


def enabled():
  """Whether the project turned login links on (CMNSD_LOGIN_LINKS)."""
  return bool(getattr(settings, 'CMNSD_LOGIN_LINKS', False))


def max_age(purpose):
  seconds = {
    LoginLink.Purpose.INVITE: getattr(settings, 'CMNSD_LOGIN_LINK_INVITE_MAX_AGE', 7 * 24 * 3600),
    LoginLink.Purpose.REQUEST: getattr(settings, 'CMNSD_LOGIN_LINK_REQUEST_MAX_AGE', 15 * 60),
  }[purpose]
  return timedelta(seconds=seconds)


def requests_per_hour():
  return getattr(settings, 'CMNSD_LOGIN_LINK_REQUESTS_PER_HOUR', 3)


def token_hash(token):
  return hashlib.sha256(token.encode()).hexdigest()


def safe_next(next_url, request):
  """An internal path to land on, or '' - never another site."""
  if next_url and next_url.startswith('/') and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
    return next_url
  return ''


def _log(actor, user, message):
  """On the user's admin history - by `actor` (who sent or revoked it; the
  user themself for their own request or use)."""
  LogEntry.objects.log_actions(actor.pk, [user], CHANGE, change_message=message, single_object=True)


def create(user, purpose, created_by=None, next_url=''):
  """A new link: (LoginLink, token). The user's open links of the same
  purpose are revoked first - only the newest works."""
  revoke_open(user, purpose, by=created_by)
  token = secrets.token_urlsafe(32)
  link = LoginLink.objects.create(
    user=user, purpose=purpose, created_by=created_by, next=next_url,
    token_hash=token_hash(token), expires_at=timezone.now() + max_age(purpose),
  )
  return link, token


def find(token):
  """The link with this token, or None - looked up by the token's hash."""
  if not token:
    return None
  return LoginLink.objects.select_related('user').filter(token_hash=token_hash(token)).first()


def revoke(link, by=None):
  if link.state != 'open':
    return False
  link.revoked_at, link.revoked_by = timezone.now(), by
  link.save(update_fields=['revoked_at', 'revoked_by'])
  _log(by or link.user, link.user, f"Login link revoked ({link.purpose})")
  return True


def revoke_open(user, purpose=None, by=None):
  links = LoginLink.objects.open().filter(user=user)
  if purpose:
    links = links.filter(purpose=purpose)
  return sum(revoke(link, by) for link in links)


def refusal(sender, recipient):
  """Why `sender` may not send `recipient` a login link - '' if they may."""
  if not (sender.is_staff and sender.has_perm('auth.change_user')):
    return _("You may not send login links.")
  if not recipient.email:
    return _("no email address")
  if not recipient.is_active:
    return _("not active - or waiting for approval")
  return ''


def may_copy(sender):
  """Whether `sender` may copy login links to pass on themselves."""
  return enabled() and bool(sender and sender.is_authenticated and sender.is_active and sender.is_superuser)


def copy_refusal(sender, recipient):
  """Why `sender` may not copy a login link for `recipient` - '' if they
  may. No address needed: the link doesn't go by mail."""
  if not may_copy(sender):
    return _("Only a superuser may copy a login link.")
  if not recipient.is_active:
    return _("not active - or waiting for approval")
  return ''


def copy(request, user, sender):
  """Make an invite to pass on without a mail: (LoginLink, its address).
  The address is only in this answer - shown once."""
  link, token = create(user, LoginLink.Purpose.INVITE, created_by=sender)
  _log(sender, user, "Login link copied")
  return link, request.build_absolute_uri(reverse('login_link', args=[token]))


def _language(user, purpose):
  """The user's chosen language - else, for their own request, the one
  they're using the site in now; for an invite, the site's."""
  preferences = getattr(user, 'preferences', None)
  chosen = getattr(preferences, 'language', '')
  if chosen:
    return chosen
  return translation.get_language() if purpose == LoginLink.Purpose.REQUEST else settings.LANGUAGE_CODE


def send(request, user, purpose, sender=None, message='', next_url=''):
  """Make a link and mail it to the user, in their language. Returns the
  LoginLink. Raises what the mail backend raises - the caller decides
  whether to say so (staff) or not (a request: the same answer always)."""
  next_url = safe_next(next_url, request)
  link, token = create(user, purpose, created_by=sender, next_url=next_url)
  context = {
    'user': user, 'sender': sender, 'message': message.strip(), 'purpose': purpose,
    'url': request.build_absolute_uri(reverse('login_link', args=[token])),
    'expires_at': link.expires_at, 'site_name': getattr(settings, 'SITE_NAME', ''),
  }
  with translation.override(_language(user, purpose)):
    subject = ' '.join(render_to_string('auth/mail/login_link_subject.txt', context).split())
    mail = EmailMultiAlternatives(subject, render_to_string('auth/mail/login_link.txt', context), settings.DEFAULT_FROM_EMAIL, [user.email])
    mail.attach_alternative(render_to_string('auth/mail/login_link.html', context), 'text/html')
  mail.send()
  _log(sender or user, user, "Login link sent" if sender else "Login link requested")
  return link


def requested_recently(user):
  """How many request links this account had in the past hour."""
  return LoginLink.objects.filter(user=user, purpose=LoginLink.Purpose.REQUEST, created_at__gte=timezone.now() - timedelta(hours=1)).count()


def use(request, link):
  """Log in with a valid link - once: it's used from now on."""
  link.used_at = timezone.now()
  link.save(update_fields=['used_at'])
  login(request, link.user, backend=BACKEND)
  _log(link.user, link.user, f"Logged in with a login link ({link.purpose})")


def cleanup(days=30):
  """Delete used, revoked and expired links older than `days`. Returns how many."""
  old = timezone.now() - timedelta(days=days)
  gone, _counts = LoginLink.objects.filter(created_at__lt=old).exclude(
    used_at=None, revoked_at=None, expires_at__gt=timezone.now(),
  ).delete()
  return gone
