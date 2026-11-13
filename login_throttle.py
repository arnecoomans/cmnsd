"""
Limit password guesses: after too many failed sign-ins, a username - or an
address trying many usernames - is refused for a while.

- Per account: CMNSD_LOGIN_ATTEMPTS_PER_ACCOUNT failures (5) within
  CMNSD_LOGIN_ATTEMPTS_WINDOW seconds (15 minutes) - by the username typed,
  whether it exists or not: the answer says nothing about who has an
  account.
- Per address: CMNSD_LOGIN_ATTEMPTS_PER_IP failures (20) in the same
  window - someone trying many usernames. Only when the address is known
  (client_ip): never one shared bucket for everyone.
- 0 turns a limit off.

Refused through an authentication backend (ThrottleBackend, first in
AUTHENTICATION_BACKENDS): it raises PermissionDenied before any password
is checked, so every sign-in - the site's form, the admin's - is covered.
Failures are counted on Django's user_login_failed signal, a success
clears its account's count. Login links and password reset don't go
through authenticate(): they stay open to the real user.

Counted in the default cache - one shared by all worker processes (a
database or file cache); a local-memory cache counts per process.
"""

import hashlib
import logging
import time

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.dispatch import receiver

logger = logging.getLogger(__name__)

BACKEND = 'cmnsd.login_throttle.ThrottleBackend'


def per_account():
  return getattr(settings, 'CMNSD_LOGIN_ATTEMPTS_PER_ACCOUNT', 5)


def per_ip():
  return getattr(settings, 'CMNSD_LOGIN_ATTEMPTS_PER_IP', 20)


def window():
  return getattr(settings, 'CMNSD_LOGIN_ATTEMPTS_WINDOW', 15 * 60)


def client_ip(request):
  """The visitor's address. Behind CMNSD_PROXY_COUNT trusted proxies
  (nginx: 1), the entry they added to X-Forwarded-For, counted from the
  right - what the client sends itself comes before it and is never
  trusted. Else REMOTE_ADDR. '' when unknown (gunicorn on a unix socket
  without a proxy header)."""
  if request is None:
    return ''
  proxies = getattr(settings, 'CMNSD_PROXY_COUNT', 0)
  if proxies:
    forwarded = [part.strip() for part in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') if part.strip()]
    if len(forwarded) >= proxies:
      return forwarded[-proxies]
  return request.META.get('REMOTE_ADDR', '')


def _keys(request, username):
  """(account key, address key or None) - the username hashed: no
  credentials in the cache."""
  name = hashlib.sha256((username or '').strip().lower().encode()).hexdigest()
  ip = client_ip(request)
  return f'cmnsd:login:account:{name}', (f'cmnsd:login:ip:{ip}' if ip else None)


def _count(key):
  """Failures within the window - checked here too, not only by the
  cache's own expiry."""
  value = cache.get(key)
  if not value or time.time() - value[1] >= window():
    return 0
  return value[0]


def _add(key):
  """One more failure - within the window started by the first one: the
  stored (count, started) keeps that start, whatever the cache's incr does
  with timeouts."""
  count, started = cache.get(key) or (0, time.time())
  remaining = window() - (time.time() - started)
  if remaining > 0:
    cache.set(key, (count + 1, started), remaining)
  else:
    cache.set(key, (1, time.time()), window())


def blocked(request, username):
  """Whether a sign-in for `username` from this request is refused now."""
  account, address = _keys(request, username)
  if per_account() and _count(account) >= per_account():
    return True
  return bool(address and per_ip() and _count(address) >= per_ip())


class ThrottleBackend:
  """First in AUTHENTICATION_BACKENDS: refuses - before any password is
  checked - a username or address over its limit. Checks no password
  itself: the backends after it do. A session it's named in (a login that
  names no backend takes the first - force_login) finds its user as
  ModelBackend does."""

  def authenticate(self, request, username=None, **credentials):
    if username is not None and blocked(request, username):
      request_ip = client_ip(request)
      logger.warning(f"Login refused, too many attempts: {username} from {request_ip}")
      if request is not None:
        request.login_throttled = True
      raise PermissionDenied
    return None

  def get_user(self, user_id):
    from django.contrib.auth.backends import ModelBackend
    return ModelBackend().get_user(user_id)


@receiver(user_login_failed)
def count_failure(sender, credentials, request=None, **kwargs):
  if request is not None and getattr(request, 'login_throttled', False):
    return   # refused before trying: not another guess
  account, address = _keys(request, credentials.get('username'))
  _add(account)
  if address:
    _add(address)


@receiver(user_logged_in)
def clear_account(sender, request, user, **kwargs):
  """Signed in: their own count starts over (an address's stays)."""
  cache.delete(_keys(request, user.get_username())[0])
