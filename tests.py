from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.utils import translation

from cmnsd.middleware.user_language import UserLanguageMiddleware

# The project's concrete Preferences (BasePreferences subclass), found via
# the user relation - cmnsd's tests don't import a project app.
Preferences = get_user_model().preferences.related.related_model


class UserLanguageMiddlewareTests(TestCase):
  def setUp(self):
    self.user = get_user_model().objects.create(username='someone')
    self.seen = None

  def run_middleware(self, user):
    def view(request):
      self.seen = translation.get_language()
      return None
    request = RequestFactory().get('/')
    request.user = user
    with translation.override('en'):
      UserLanguageMiddleware(view)(request)
    return self.seen

  def test_without_preferences_keeps_default(self):
    self.assertEqual(self.run_middleware(self.user), 'en')

  def test_preferred_language_is_activated(self):
    Preferences.objects.create(user=self.user, language='nl')
    self.user.refresh_from_db()
    self.assertEqual(self.run_middleware(self.user), 'nl')

  def test_anonymous_untouched(self):
    self.assertEqual(self.run_middleware(AnonymousUser()), 'en')

  def test_other_errors_are_not_swallowed(self):
    Preferences.objects.create(user=self.user, language='nl')
    self.user.refresh_from_db()
    with mock.patch.object(Preferences, 'language', new_callable=mock.PropertyMock, side_effect=RuntimeError('bug')):
      with self.assertRaises(RuntimeError):
        self.run_middleware(self.user)
