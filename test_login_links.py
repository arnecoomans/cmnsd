import re
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from cmnsd import login_links
from cmnsd.models import LoginLink

LINK = re.compile(r'https?://[^/\s]+(/accounts/login/link/[A-Za-z0-9_-]+/)')


@override_settings(CMNSD_LOGIN_LINKS=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class LoginLinkTests(TestCase):
  """Login links (cmnsd/login_links.py): a mailed link that signs in once -
  sent by staff (an invite) or asked for on the login page (a request).
  Stored as a hash; revocable; only through the button; only for an active
  account - staff too, yourself too."""

  def setUp(self):
    User = get_user_model()
    self.staff = User.objects.create(username='beheer', email='beheer@example.org', is_staff=True)
    self.staff.user_permissions.add(Permission.objects.get(codename='change_user'))
    self.staff.save()
    self.ilse = User.objects.create(username='ilse', email='ilse@example.org')
    self.ilse.set_unusable_password()
    self.ilse.save()
    self.staff_client = Client()
    self.staff_client.force_login(self.staff)

  def invite(self, *users, client=None, **data):
    return (client or self.staff_client).post('/accounts/login/link/send/', {'user': [user.pk for user in users], **data})

  def mailed_path(self, index=-1):
    return LINK.search(mail.outbox[index].body).group(1)

  def test_off_unless_turned_on(self):
    with override_settings(CMNSD_LOGIN_LINKS=False):
      self.assertEqual(self.client.get('/accounts/login/link/').status_code, 404)
      self.assertEqual(self.staff_client.get(f'/accounts/login/link/send/?user={self.ilse.pk}').status_code, 404)
      self.assertNotIn('/accounts/login/link/', self.client.get('/accounts/login/').content.decode())
    self.assertIn('/accounts/login/link/', self.client.get('/accounts/login/').content.decode())

  def test_an_invite_signs_in_once_through_the_button(self):
    self.invite(self.ilse, message='Kijk eens naar de trouwfoto', next='/people/')
    self.assertEqual(len(mail.outbox), 1)
    self.assertIn('Kijk eens naar de trouwfoto', mail.outbox[0].body)
    path = self.mailed_path()
    token = path.rstrip('/').rsplit('/', 1)[1]
    self.assertFalse(LoginLink.objects.filter(token_hash=token).exists())        # only its hash is stored
    client = Client()
    self.assertEqual(client.get(path).status_code, 200)                         # a scanner opening it: nothing used
    self.assertNotIn('_auth_user_id', client.session)
    response = client.post(path)
    self.assertRedirects(response, '/people/', fetch_redirect_response=False)
    self.assertEqual(int(client.session['_auth_user_id']), self.ilse.pk)
    self.assertEqual(Client().post(path).status_code, 410)                      # once
    self.assertIn('used already', Client().get(path).content.decode())

  def test_used_again_while_signed_in(self):
    """Their own link a second time: on to where it leads, no error.
    Someone else's: the error, and who they're signed in as."""
    self.invite(self.ilse, next='/people/')
    path = self.mailed_path()
    client = Client()
    client.post(path)
    self.assertRedirects(client.get(path), '/people/', fetch_redirect_response=False)
    self.assertRedirects(client.post(path), '/people/', fetch_redirect_response=False)
    page = self.staff_client.get(path)
    self.assertEqual(page.status_code, 410)
    self.assertContains(page, "signed in as beheer", status_code=410)
    self.assertNotContains(page, '/accounts/login/link/"', status_code=410)

  def test_revoked_and_expired(self):
    self.invite(self.ilse)
    path = self.mailed_path()
    login_links.revoke(LoginLink.objects.get(), by=self.staff)
    self.assertEqual(Client().post(path).status_code, 410)
    self.assertIn('revoked', Client().get(path).content.decode())
    self.invite(self.ilse)
    LoginLink.objects.filter(revoked_at=None).update(expires_at=timezone.now() - timedelta(minutes=1))
    self.assertEqual(Client().post(self.mailed_path()).status_code, 410)
    self.assertEqual(Client().get('/accounts/login/link/nonsense/').status_code, 410)   # unknown reads as expired

  def test_sending_again_replaces_the_open_invite(self):
    self.invite(self.ilse)
    first = self.mailed_path()
    self.invite(self.ilse)
    self.assertEqual(Client().post(first).status_code, 410)
    self.assertEqual(Client().post(self.mailed_path()).status_code, 302)

  def test_inactive_never(self):
    self.invite(self.ilse)
    path = self.mailed_path()
    self.ilse.is_active = False
    self.ilse.save()
    self.assertEqual(Client().post(path).status_code, 410)
    mail.outbox.clear()
    self.invite(self.ilse)
    self.assertEqual(len(mail.outbox), 0)                                       # not sent: waiting for approval

  def test_a_staff_account_and_yourself(self):
    """Staff accounts like any other; and to yourself - another device."""
    other = get_user_model().objects.create(username='collega', email='c@example.org', is_staff=True)
    self.invite(other, self.staff)
    self.assertEqual(sorted(message.to[0] for message in mail.outbox), ['beheer@example.org', 'c@example.org'])

  def test_only_staff_who_may_change_users_send(self):
    client = Client()
    client.force_login(self.ilse)
    self.assertEqual(self.invite(self.ilse, client=client).status_code, 404)
    self.assertEqual(len(mail.outbox), 0)

  def test_next_only_internal(self):
    self.invite(self.ilse, next='https://evil.example.com/')
    self.assertEqual(LoginLink.objects.get().next, '')
    self.assertRedirects(Client().post(self.mailed_path()), settings.LOGIN_REDIRECT_URL, fetch_redirect_response=False)   # where a password login lands

  def test_request_the_same_answer_and_a_limit(self):
    known = self.client.post('/accounts/login/link/', {'email': 'ILSE@example.org'}).content.decode()
    unknown = self.client.post('/accounts/login/link/', {'email': 'nobody@example.org'}).content.decode()
    self.assertEqual(len(mail.outbox), 1)
    self.assertIn('If ilse@example.org belongs to an account', known.replace('ILSE', 'ilse'))
    self.assertIn('If nobody@example.org belongs to an account', unknown)
    for _ in range(5):
      self.client.post('/accounts/login/link/', {'email': 'ilse@example.org'})
    self.assertEqual(len(mail.outbox), login_links.requests_per_hour())         # then nothing more this hour
    self.assertEqual(LoginLink.objects.open().filter(user=self.ilse).count(), 1)   # only the newest request works
    self.assertRedirects(Client().post(self.mailed_path()), settings.LOGIN_REDIRECT_URL, fetch_redirect_response=False)   # where a password login lands

  def test_a_request_in_the_language_of_the_page(self):
    """No language chosen: a request comes in the language the site was
    used in (the sign-in page), not the site's default."""
    self.client.post('/accounts/login/link/', {'email': 'ilse@example.org'}, HTTP_ACCEPT_LANGUAGE='nl')
    self.assertIn('Log in met deze link', mail.outbox[0].body)

  def test_revoke_from_the_profile(self):
    self.invite(self.ilse)
    link = LoginLink.objects.get()
    client = Client()
    client.force_login(self.ilse)
    self.assertIn(f'/accounts/login/link/{link.pk}/revoke/', client.get('/accounts/profile/').content.decode())
    client.post(f'/accounts/login/link/{link.pk}/revoke/')
    link.refresh_from_db()
    self.assertEqual(link.state, 'revoked')

  def test_logged_never_the_token(self):
    self.invite(self.ilse)
    path = self.mailed_path()
    Client().post(path)
    messages = list(LogEntry.objects.filter(object_id=str(self.ilse.pk)).values_list('change_message', flat=True))
    self.assertIn('Login link sent', messages)
    self.assertIn('Logged in with a login link (invite)', messages)
    self.assertFalse(any(path.strip('/').rsplit('/', 1)[1] in message for message in messages))

  def test_cleanup(self):
    self.invite(self.ilse)
    self.invite(self.ilse)                                                        # the first is revoked
    LoginLink.objects.update(created_at=timezone.now() - timedelta(days=40))
    self.assertEqual(login_links.cleanup(30), 1)                                 # the open one stays

  def test_the_users_admin_page(self):
    """The user's page in the admin: their links, and "send login link"."""
    self.staff.is_superuser = True
    self.staff.save()
    self.invite(self.ilse)
    page = self.staff_client.get(f'/admin/auth/user/{self.ilse.pk}/change/')
    self.assertEqual(page.status_code, 200)
    self.assertContains(page, f'/accounts/login/link/send/?user={self.ilse.pk}')
    self.assertEqual(self.staff_client.get(f'/admin/auth/user/{self.staff.pk}/change/').status_code, 200)   # without links too

  def test_the_admin_action(self):
    self.staff.is_superuser = True
    self.staff.save()
    response = self.staff_client.post('/admin/auth/user/', {'action': 'send_login_link', '_selected_action': [self.ilse.pk]})
    self.assertEqual(response.status_code, 302)
    self.assertIn(f'/accounts/login/link/send/?user={self.ilse.pk}', response['Location'])
    self.assertContains(self.staff_client.get(response['Location']), 'ilse@example.org')
    with override_settings(CMNSD_LOGIN_LINKS=False):
      self.assertNotContains(self.staff_client.get('/admin/auth/user/'), 'send_login_link')
