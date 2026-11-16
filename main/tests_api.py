"""Tes fondasi web service DRF untuk aplikasi Flutter: endpoint auth, CSRF, CORS, dan routing."""
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import include, path, resolve, reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.test import APIClient

PWS_HOST = settings.PWS_HOST
PWS_ORIGIN = f'https://{PWS_HOST}'


@api_view(['GET', 'POST'])
def write_probe(request):
    """View tanpa dekorator auth/permission: memakai default REST_FRAMEWORK proyek."""
    return Response({'user': request.user.username, 'method': request.method})


urlpatterns = [
    path('api/auth/', include('main.api_urls')),
    path('api/probe/', write_probe),
]


class ApiTestCase(TestCase):
    password = 'Necro-pass-2026!'

    def setUp(self):
        cache.clear()  # penghitung LoginThrottle dan throttle register disimpan di cache
        self.user = User.objects.create_user('evan', password=self.password)
        self.client = APIClient()

    def login(self, client=None, **extra):
        client = client or self.client
        return client.post(
            reverse('auth_api:login'), {'username': 'evan', 'password': self.password},
            format='json', **extra,
        )


class SetupTest(TestCase):
    def test_drf_and_cors_installed(self):
        self.assertIn('rest_framework', settings.INSTALLED_APPS)
        self.assertIn('corsheaders', settings.INSTALLED_APPS)
        middleware = settings.MIDDLEWARE
        self.assertLess(
            middleware.index('corsheaders.middleware.CorsMiddleware'),
            middleware.index('django.middleware.common.CommonMiddleware'),
        )

    def test_default_api_policy_is_session_and_authenticated(self):
        config = settings.REST_FRAMEWORK
        self.assertEqual(
            config['DEFAULT_AUTHENTICATION_CLASSES'],
            ['rest_framework.authentication.SessionAuthentication'],
        )
        self.assertEqual(
            config['DEFAULT_PERMISSION_CLASSES'], ['rest_framework.permissions.IsAuthenticated'],
        )

    def test_android_emulator_and_pws_hosts_allowed(self):
        self.assertIn('10.0.2.2', settings.ALLOWED_HOSTS)
        self.assertIn(PWS_HOST, settings.ALLOWED_HOSTS)
        self.assertIn(PWS_ORIGIN, settings.CSRF_TRUSTED_ORIGINS)

    def test_auth_routes_resolve(self):
        for name, url in [
            ('login', '/api/auth/login/'), ('register', '/api/auth/register/'),
            ('logout', '/api/auth/logout/'), ('me', '/api/auth/me/'), ('csrf', '/api/auth/csrf/'),
        ]:
            self.assertEqual(reverse(f'auth_api:{name}'), url)
            self.assertEqual(resolve(url).namespace, 'auth_api')

    def test_module_api_skeletons_are_mounted(self):
        """Setiap modul punya api_urls yang ter-include; route-nya diisi masing-masing anggota."""
        import importlib

        from django.urls import get_resolver

        mounted = {
            str(p.pattern): p.urlconf_module.__name__
            for p in get_resolver().url_patterns
            if hasattr(p, 'urlconf_module') and not isinstance(p.urlconf_module, list)
        }
        expected = {
            'api/death-clock/': 'death_clock.api_urls',
            'api/recipes/': 'recipe_alchemist.api_urls',
            'api/dead-drop/': 'dead_drop.api_urls',
            'api/graveyard/': 'graveyard.api_urls',
            'api/grimoire/': 'preservation_grimoire.api_urls',
        }
        for prefix, module in expected.items():
            self.assertEqual(mounted.get(prefix), module)
            app = module.split('.')[0]
            importlib.import_module(f'{app}.serializers')
            importlib.import_module(f'{app}.api_views')

    def test_legacy_json_endpoints_untouched(self):
        self.assertEqual(reverse('death_clock:pantry_json'), '/death-clock/json/')
        self.assertEqual(reverse('preservation_grimoire:grimoire_json'), '/grimoire/json/')


class LoginApiTest(ApiTestCase):
    def test_login_json_success_starts_session_and_returns_csrf(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIs(body['status'], True)
        self.assertEqual(body['username'], 'evan')
        self.assertEqual(body['user'], {'id': self.user.pk, 'username': 'evan'})
        self.assertTrue(body['csrf_token'])
        self.assertIn('csrftoken', response.cookies)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_login_form_encoded_like_cookie_request(self):
        response = self.client.post(
            reverse('auth_api:login'), {'username': 'evan', 'password': self.password},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()['status'], True)

    def test_login_wrong_password_401(self):
        response = self.client.post(
            reverse('auth_api:login'), {'username': 'evan', 'password': 'salah'}, format='json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'status': False, 'message': 'Username atau password salah.'})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_missing_fields_400(self):
        response = self.client.post(reverse('auth_api:login'), {'username': 'evan'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIs(response.json()['status'], False)

    def test_login_non_object_json_400(self):
        response = self.client.post(reverse('auth_api:login'), ['evan'], format='json')
        self.assertEqual(response.status_code, 400)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.login().status_code, 401)

    def test_login_locked_after_repeated_failures(self):
        for _ in range(5):
            self.client.post(
                reverse('auth_api:login'), {'username': 'evan', 'password': 'salah'}, format='json',
            )
        response = self.login()  # password benar pun ditolak selama terkunci
        self.assertEqual(response.status_code, 429)
        self.assertIs(response.json()['status'], False)
        self.assertIn('Retry-After', response)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse('auth_api:login')).status_code, 405)


class RegisterApiTest(ApiTestCase):
    def register(self, **data):
        payload = {'username': 'syarif', 'password1': self.password, 'password2': self.password}
        payload.update(data)
        return self.client.post(reverse('auth_api:register'), payload, format='json')

    def test_register_success_creates_user_without_login(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIs(body['status'], True)
        self.assertEqual(body['username'], 'syarif')
        self.assertTrue(User.objects.get(username='syarif').check_password(self.password))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_register_password_mismatch_has_field_errors(self):
        response = self.register(password2='beda-sekali-123')
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIs(body['status'], False)
        self.assertIn('password2', body['errors'])
        self.assertEqual(body['message'], body['errors']['password2'][0])
        self.assertFalse(User.objects.filter(username='syarif').exists())

    def test_register_duplicate_username_rejected(self):
        response = self.register(username='Evan')  # beda huruf besar-kecil tetap dianggap sama
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.json()['errors'])

    def test_register_weak_password_rejected(self):
        response = self.register(password1='12345678', password2='12345678')
        self.assertEqual(response.status_code, 400)
        self.assertIn('password2', response.json()['errors'])

    def test_register_is_throttled(self):
        for i in range(10):
            self.assertEqual(self.register(username=f'user{i}').status_code, 201)
        self.assertEqual(self.register(username='user10').status_code, 429)


class SessionApiTest(ApiTestCase):
    def test_me_for_guest_and_logged_in_user(self):
        response = self.client.get(reverse('auth_api:me'))
        self.assertEqual(response.json(), {'status': True, 'is_authenticated': False, 'user': None})
        self.login()
        response = self.client.get(reverse('auth_api:me'))
        self.assertEqual(response.json()['user'], {'id': self.user.pk, 'username': 'evan'})
        self.assertIs(response.json()['is_authenticated'], True)

    def test_csrf_endpoint_sets_cookie(self):
        response = self.client.get(reverse('auth_api:csrf'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['csrf_token'])
        self.assertIn('csrftoken', response.cookies)

    def test_logout_ends_session(self):
        self.login()
        response = self.client.post(reverse('auth_api:logout'), format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['username'], 'evan')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertIs(self.client.get(reverse('auth_api:me')).json()['is_authenticated'], False)

    def test_logout_needs_no_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        self.login(client)
        self.assertEqual(client.post(reverse('auth_api:logout')).status_code, 200)

    def test_logout_get_not_allowed(self):
        self.login()
        self.assertEqual(self.client.get(reverse('auth_api:logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)


@override_settings(ROOT_URLCONF=__name__)
class DefaultPolicyAndCsrfTest(ApiTestCase):
    """Membuktikan alur request tulis Flutter yang dijelaskan di docs/API_MOBILE.md."""

    def test_guest_gets_403_from_default_policy(self):
        response = self.client.get('/api/probe/')
        self.assertEqual(response.status_code, 403)
        self.assertIn('detail', response.json())

    def test_logged_in_read_needs_no_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        self.login(client)
        response = client.get('/api/probe/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user'], 'evan')

    def test_write_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        self.login(client)
        response = client.post('/api/probe/', {}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('CSRF', response.json()['detail'])

    def test_write_with_token_and_origin_over_https_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        token = self.login(client, secure=True, HTTP_HOST=PWS_HOST).json()['csrf_token']
        response = client.post(
            '/api/probe/', {}, format='json', secure=True, HTTP_HOST=PWS_HOST,
            HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=PWS_ORIGIN,
        )
        self.assertEqual(response.status_code, 200)

    def test_write_over_https_without_origin_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        token = self.login(client, secure=True, HTTP_HOST=PWS_HOST).json()['csrf_token']
        response = client.post(
            '/api/probe/', {}, format='json', secure=True, HTTP_HOST=PWS_HOST,
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('Referer checking failed', response.json()['detail'])

    def test_write_behind_http_proxy_with_trusted_origin_succeeds(self):
        """Jika PWS meneruskan request sebagai HTTP, Origin https PWS tetap dipercaya."""
        client = APIClient(enforce_csrf_checks=True)
        token = self.login(client, HTTP_HOST=PWS_HOST).json()['csrf_token']
        response = client.post(
            '/api/probe/', {}, format='json', HTTP_HOST=PWS_HOST,
            HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=PWS_ORIGIN,
        )
        self.assertEqual(response.status_code, 200)

    def test_write_from_untrusted_origin_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        token = self.login(client, secure=True, HTTP_HOST=PWS_HOST).json()['csrf_token']
        response = client.post(
            '/api/probe/', {}, format='json', secure=True, HTTP_HOST=PWS_HOST,
            HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN='https://evil.example',
        )
        self.assertEqual(response.status_code, 403)


class CorsTest(TestCase):
    def preflight(self, path, origin):
        return self.client.options(
            path, HTTP_ORIGIN=origin, HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type,x-csrftoken',
        )

    def test_flutter_web_origin_allowed_on_api_with_credentials(self):
        response = self.preflight('/api/auth/login/', 'http://localhost:5000')
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://localhost:5000')
        self.assertEqual(response['Access-Control-Allow-Credentials'], 'true')
        self.assertIn('x-csrftoken', response['Access-Control-Allow-Headers'])

    def test_other_origins_and_ports_not_allowed(self):
        for origin in ['https://evil.example', 'http://localhost:5173']:
            response = self.preflight('/api/auth/login/', origin)
            self.assertNotIn('Access-Control-Allow-Origin', response)

    def test_cors_only_applies_to_api_paths(self):
        response = self.client.get('/death-clock/json/', HTTP_ORIGIN='http://localhost:5000')
        self.assertNotIn('Access-Control-Allow-Origin', response)
