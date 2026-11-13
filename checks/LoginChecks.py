from django.conf import settings
from django.core.checks import register, Warning

from cmnsd import login_throttle


@register()
def check_login_throttle(app_configs, **kwargs):
  """Password guesses are only limited when ThrottleBackend is asked first
  (cmnsd/login_throttle.py) - a site that leaves it out has no limit, and
  nothing else would say so."""
  if not (login_throttle.per_account() or login_throttle.per_ip()):
    return []
  backends = list(getattr(settings, 'AUTHENTICATION_BACKENDS', []))
  if backends[:1] != [login_throttle.BACKEND]:
    return [Warning(
      "Password guesses aren't limited: cmnsd's ThrottleBackend isn't first in AUTHENTICATION_BACKENDS.",
      hint=f"AUTHENTICATION_BACKENDS = ['{login_throttle.BACKEND}', 'django.contrib.auth.backends.ModelBackend'] - "
           "or set CMNSD_LOGIN_ATTEMPTS_PER_ACCOUNT and CMNSD_LOGIN_ATTEMPTS_PER_IP to 0.",
      id='cmnsd.auth.W001',
    )]
  return []
