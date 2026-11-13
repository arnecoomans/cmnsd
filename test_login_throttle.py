from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.checks import run_checks
from django.test import Client, RequestFactory, TestCase, override_settings

from cmnsd import login_throttle


@override_settings(
  AUTHENTICATION_BACKENDS=[login_throttle.BACKEND, 'django.contrib.auth.backends.ModelBackend'],
  CMNSD_LOGIN_ATTEMPTS_PER_ACCOUNT=3, CMNSD_LOGIN_ATTEMPTS_PER_IP=5, CMNSD_LOGIN_ATTEMPTS_WINDOW=900,
  CMNSD_PROXY_COUNT=0,
)
class LoginThrottleTests(TestCase):
  """Password guesses (cmnsd/login_throttle.py): a username, or an address,
  over its limit is refused before any password is checked - on the site's
  form and the admin's; a success starts its account over."""

  def setUp(self):
    cache.clear()
    self.ilse = get_user_model().objects.create_user('ilse', password='a-long-passphrase')

  def sign_in(self, username='ilse', password='wrong', path='/accounts/login/', client=None, ip='10.0.0.1'):
    return (client or Client()).post(path, {'username': username, 'password': password}, REMOTE_ADDR=ip)

  def signed_in(self, response):
    return response.status_code == 302

  def test_an_account_after_too_many_guesses(self):
    for _ in range(3):
      self.assertFalse(self.signed_in(self.sign_in()))
    response = self.sign_in(password='a-long-passphrase')                  # the right one, too late
    self.assertFalse(self.signed_in(response))
    self.assertIn('Too many attempts', response.content.decode())
    self.assertFalse(self.signed_in(self.sign_in(username='ILSE', password='a-long-passphrase', ip='10.0.0.2')))   # the account, from anywhere
    self.assertFalse(self.signed_in(self.sign_in(password='a-long-passphrase', path='/admin/login/')))           # the admin too

  def test_the_window_passes(self):
    for _ in range(3):
      self.sign_in()
    key = login_throttle._keys(None, 'ilse')[0]
    count, started = cache.get(key)
    cache.set(key, (count, started - 901), 900)                             # as if 15 minutes went by
    self.assertTrue(self.signed_in(self.sign_in(password='a-long-passphrase')))

  def test_a_success_starts_over(self):
    for _ in range(2):
      self.sign_in()
    self.assertTrue(self.signed_in(self.sign_in(password='a-long-passphrase')))
    for _ in range(2):
      self.sign_in()
    self.assertTrue(self.signed_in(self.sign_in(password='a-long-passphrase')))

  def test_an_address_trying_many_names(self):
    for name in ('a', 'b', 'c', 'd', 'e'):
      self.sign_in(username=name)
    self.assertFalse(self.signed_in(self.sign_in(password='a-long-passphrase')))
    self.assertTrue(self.signed_in(self.sign_in(password='a-long-passphrase', ip='10.0.0.9')))   # someone else

  def test_no_address_no_shared_limit(self):
    """Without a known address (a unix socket, no proxy header) no one is
    lumped together: only the account limit counts."""
    for name in ('a', 'b', 'c', 'd', 'e', 'f'):
      self.sign_in(username=name, ip='')
    self.assertTrue(self.signed_in(self.sign_in(password='a-long-passphrase', ip='')))

  def test_off(self):
    with self.settings(CMNSD_LOGIN_ATTEMPTS_PER_ACCOUNT=0, CMNSD_LOGIN_ATTEMPTS_PER_IP=0):
      for _ in range(10):
        self.sign_in()
      self.assertTrue(self.signed_in(self.sign_in(password='a-long-passphrase')))

  def test_client_ip_behind_a_proxy(self):
    request = RequestFactory().get('/', REMOTE_ADDR='', HTTP_X_FORWARDED_FOR='6.6.6.6, 203.0.113.7')
    self.assertEqual(login_throttle.client_ip(request), '')
    with self.settings(CMNSD_PROXY_COUNT=1):
      self.assertEqual(login_throttle.client_ip(request), '203.0.113.7')   # nginx's entry, not what the client sent
      self.assertEqual(login_throttle.client_ip(RequestFactory().get('/', REMOTE_ADDR='127.0.0.1')), '127.0.0.1')

  def test_the_check(self):
    ids = lambda: [message.id for message in run_checks()]
    self.assertNotIn('cmnsd.auth.W001', ids())
    with self.settings(AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend']):
      self.assertIn('cmnsd.auth.W001', ids())
