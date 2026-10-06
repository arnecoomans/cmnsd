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


class EditModeTests(TestCase):
  """The edit-mode switch (cmnsd/edit/mode.py, cmnsd_ui:edit_mode): only
  for users with a change permission, kept in the session, and the
  per-object check (can_edit) stays separate from the switch."""

  def setUp(self):
    from django.contrib.auth.models import Permission
    self.editor = get_user_model().objects.create(username='editor')
    self.editor.user_permissions.add(Permission.objects.get(codename='change_permission'))
    self.member = get_user_model().objects.create(username='member')

  def login(self, user):
    from django.test import Client
    client = Client()
    user.save()
    client.force_login(user)
    return client

  def switch(self, client, on, next_url='/accounts/'):
    return client.post('/ui/edit/', {'on': '1' if on else '0', 'next': next_url})

  def test_editor_switches_on_and_off_and_returns(self):
    client = self.login(self.editor)
    response = self.switch(client, True, '/accounts/profile/')
    self.assertRedirects(response, '/accounts/profile/', fetch_redirect_response=False)
    self.assertTrue(client.session.get('cmnsd_edit_mode'))
    self.switch(client, False)
    self.assertIsNone(client.session.get('cmnsd_edit_mode'))

  def test_member_without_change_permission_is_refused(self):
    client = self.login(self.member)
    self.assertEqual(self.switch(client, True).status_code, 403)
    self.assertIsNone(client.session.get('cmnsd_edit_mode'))

  def test_signed_out_is_refused(self):
    from django.test import Client
    self.assertEqual(self.switch(Client(), True).status_code, 403)

  def test_only_same_site_redirects(self):
    response = self.switch(self.login(self.editor), True, 'https://example.com/')
    self.assertRedirects(response, '/', fetch_redirect_response=False)

  def test_get_not_allowed(self):
    self.assertEqual(self.login(self.editor).get('/ui/edit/').status_code, 405)

  def test_context_processor(self):
    from cmnsd.context_processors.edit_mode import edit_mode
    client = self.login(self.editor)
    self.switch(client, True)
    request = RequestFactory().get('/')
    request.user = self.editor
    request.session = client.session
    self.assertEqual(edit_mode(request), {'can_edit_mode': True, 'edit_mode': True})
    request.user = AnonymousUser()
    self.assertEqual(edit_mode(request), {'can_edit_mode': False, 'edit_mode': False})

  def test_losing_the_permission_ends_edit_mode(self):
    client = self.login(self.editor)
    self.switch(client, True)
    self.editor.user_permissions.clear()
    editor = get_user_model().objects.get(pk=self.editor.pk)   # fresh: permissions are cached per instance
    from cmnsd.edit.mode import is_edit_mode
    request = RequestFactory().get('/')
    request.user, request.session = editor, client.session
    self.assertFalse(is_edit_mode(request))

  def test_can_edit_is_per_model(self):
    from django.contrib.auth.models import Group, Permission
    from cmnsd.edit.mode import can_edit
    editor = get_user_model().objects.get(pk=self.editor.pk)
    self.assertTrue(can_edit(Permission.objects.first(), editor))   # holds change_permission
    self.assertFalse(can_edit(Group(name='x'), editor))              # but not change_group
    self.assertFalse(can_edit(Group(name='x'), AnonymousUser()))


class ApiResponseShapeTests(TestCase):
  """Every cmnsd API endpoint answers in one shape (cmnsd/views/api/
  response.py): ok + messages always, model/token when known, error +
  errors on an error - also a 404 or 405, never an HTML page."""

  def setUp(self):
    from django.contrib.auth.models import Permission
    from django.test import Client
    from cmnsd.api.registry import API_REGISTRY
    # A registered model with objects and a token - found through the
    # registry, so this test doesn't import a project app.
    self.user = get_user_model().objects.create(username='shape', is_staff=True, is_superuser=True)
    self.user.save()
    self.client = Client()
    self.client.force_login(self.user)
    self.model = None
    for model_cls, entry in API_REGISTRY.items():
      obj = model_cls.objects.exclude(token='').first() if hasattr(model_cls, 'token') else None
      if obj is not None:
        self.model, self.obj = entry['name'], obj
        break

  def assert_shape(self, response, status, ok):
    self.assertEqual(response.status_code, status)
    self.assertEqual(response['Content-Type'], 'application/json')
    data = response.json()
    self.assertIs(data['ok'], ok)
    self.assertIn('messages', data)
    if not ok:
      self.assertTrue(data.get('error'))
      self.assertIsInstance(data.get('errors'), dict)
    return data

  def test_not_found_is_json_everywhere(self):
    for url in ('/api/nosuchmodel/', '/api/nosuchmodel/abc/', '/api/nosuchmodel/suggest/x/',
                '/api/nosuchmodel/abc/form/x/'):
      with self.subTest(url=url):
        data = self.assert_shape(self.client.get(url), 404, False)
        self.assertEqual(data['errors'], {'not_found': True})

  def test_wrong_method_is_json(self):
    self.assert_shape(self.client.post('/api/nosuchmodel/'), 405, False)

  def test_unknown_action_and_hidden_object(self):
    if not self.model:
      self.skipTest('no registered model with objects')
    self.assert_shape(self.client.post(f'/api/{self.model}/{self.obj.token}/no_such_action/'), 404, False)
    self.assert_shape(self.client.get(f'/api/{self.model}/zzzzzzzzzz/'), 404, False)


class UiStateResponseTests(TestCase):
  """The UI-state endpoints (cmnsd/views/ui.py) read their body with the
  shared request_data() and answer in the API response shape."""

  def setUp(self):
    from django.test import Client
    self.user = get_user_model().objects.create(username='ui')
    self.user.save()
    self.client = Client()
    self.client.force_login(self.user)

  def post(self, url, body, content_type='application/json', client=None):
    return (client or self.client).post(url, body, content_type=content_type)

  def test_saved_in_the_shape(self):
    data = self.post('/ui/section/', '{"key": "person.content", "open": false}').json()
    self.assertEqual((data['ok'], data['key'], data['open']), (True, 'person.content', False))
    self.assertIn('messages', data)
    data = self.post('/ui/sort/', '{"key": "person.content", "value": "date"}').json()
    self.assertEqual((data['ok'], data['value']), (True, 'date'))

  def test_malformed_body_is_a_400_in_the_shape(self):
    for body in ('not json', '[1, 2]'):
      with self.subTest(body=body):
        response = self.post('/ui/section/', body)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertIn('request', data['errors'])

  def test_signed_out_is_a_403_in_the_shape(self):
    from django.test import Client
    response = self.post('/ui/sort/', '{"key": "a", "value": "b"}', client=Client())
    self.assertEqual(response.status_code, 403)
    self.assertEqual(response.json()['errors'], {'permission': 'sign_in'})
