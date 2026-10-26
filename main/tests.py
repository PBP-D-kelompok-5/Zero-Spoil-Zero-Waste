from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.urls import resolve, reverse

from main.auth import LoginThrottle, client_ip, rate_limit


class MainPageTest(TestCase):
    def test_main_page_exists(self):
        response = self.client.get(reverse('main:show_main'))
        self.assertEqual(response.status_code, 200)

    def test_main_page_uses_base_template(self):
        response = self.client.get(reverse('main:show_main'))
        self.assertTemplateUsed(response, 'main/home.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateUsed(response, 'partials/ambient_backdrop.html')

    def test_theme_toggle_and_ambient_backdrop_rendered(self):
        response = self.client.get(reverse('main:show_main'))
        self.assertContains(response, 'data-theme-toggle')
        self.assertContains(response, 'pn-world-village')
        self.assertContains(response, 'pn-world-graveyard')
        self.assertContains(response, 'pn-celestial-sun')
        self.assertContains(response, 'pn-celestial-moon')

    def test_main_page_lists_all_modules(self):
        response = self.client.get(reverse('main:show_main'))
        for name in ['Pantry Death Clock', 'Recipe Alchemist', 'The Dead Drop', 'The Graveyard', 'Preservation Grimoire']:
            self.assertContains(response, name)

    def test_module_cards_link_to_live_modules(self):
        response = self.client.get(reverse('main:show_main'))
        for url_name in [
            'death_clock:pantry_list',
            'recipe_alchemist:recipe_list',
            'graveyard:graveyard_list',
            'preservation_grimoire:grimoire_list',
        ]:
            self.assertContains(response, f'href="{reverse(url_name)}"')

    def test_only_unfinished_module_is_coming_soon(self):
        response = self.client.get(reverse('main:show_main'))
        self.assertContains(response, 'Segera hadir', count=1)

    def test_navbar_grimoire_links_to_module(self):
        response = self.client.get(reverse('main:show_main'))
        self.assertNotContains(response, '#grimoire"')
        self.assertContains(response, f'href="{reverse("preservation_grimoire:grimoire_list")}" class="pn-nav__link"', count=2)

    def test_grimoire_url_served_by_grimoire_module(self):
        self.assertEqual(resolve('/grimoire/').view_name, 'preservation_grimoire:grimoire_list')

    def test_nonexistent_page(self):
        response = self.client.get('/halaman-yang-tidak-ada/')
        self.assertEqual(response.status_code, 404)


class AuthTest(TestCase):
    def setUp(self):
        self.password = 'Kulkas-Bersama-2026'
        self.user = User.objects.create_user('zombie', password=self.password)

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(reverse('main:register'), {
            'username': 'necro_kost',
            'password1': self.password,
            'password2': self.password,
        })
        self.assertRedirects(response, reverse('main:show_main'))
        self.assertTrue(User.objects.filter(username='necro_kost').exists())
        self.assertIn('_auth_user_id', self.client.session)

    def test_register_with_mismatched_password_fails(self):
        response = self.client.post(reverse('main:register'), {
            'username': 'necro_kost',
            'password1': self.password,
            'password2': 'beda-sendiri-123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='necro_kost').exists())

    def test_login_success(self):
        response = self.client.post(reverse('main:login'), {'username': 'zombie', 'password': self.password})
        self.assertRedirects(response, reverse('main:show_main'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_wrong_password(self):
        response = self.client.post(reverse('main:login'), {'username': 'zombie', 'password': 'salah'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_ignores_external_next(self):
        response = self.client.post(reverse('main:login'), {
            'username': 'zombie', 'password': self.password, 'next': 'https://contoh-jahat.com/',
        })
        self.assertRedirects(response, reverse('main:show_main'))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('main:logout')).status_code, 405)
        response = self.client.post(reverse('main:logout'))
        self.assertRedirects(response, reverse('main:show_main'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_navbar_shows_username_when_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('main:show_main'))
        self.assertContains(response, 'zombie')
        self.assertContains(response, 'Keluar')

    def test_login_follows_internal_next(self):
        target = reverse('death_clock:pantry_list')
        response = self.client.post(reverse('main:login'), {
            'username': 'zombie', 'password': self.password, 'next': target,
        })
        self.assertRedirects(response, target, fetch_redirect_response=False)

    def test_logged_in_user_skips_login_and_register(self):
        self.client.force_login(self.user)
        for url_name in ['main:login', 'main:register']:
            response = self.client.get(reverse(url_name))
            self.assertRedirects(response, reverse('main:show_main'))


@override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
class ErrorPageTest(TestCase):
    def test_404_uses_custom_page(self):
        response = self.client.get('/tidak-ada-di-sini/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
        self.assertContains(response, 'sudah dikubur', status_code=404)
        self.assertContains(response, reverse('main:show_main'), status_code=404)

    def test_other_users_data_shows_same_404_page(self):
        owner = User.objects.create_user('pemilik', password='Kulkas-Bersama-2026')
        from death_clock.models import PantryItem
        item = PantryItem.objects.create(user=owner, name='Tahu', expiry_date='2026-11-01')
        self.client.force_login(User.objects.create_user('tetangga', password='Kulkas-Bersama-2026'))
        response = self.client.get(reverse('death_clock:item_update', args=[item.pk]))
        self.assertTemplateUsed(response, '404.html')

    def test_500_page_renders_without_request_context(self):
        html = render_to_string('500.html')
        self.assertIn('Terjadi galat', html)
        self.assertIn('href="/"', html)


class LoginThrottleTest(TestCase):
    """Percobaan login gagal dibatasi per (IP, username); login berhasil menghapus penghitungnya."""

    def setUp(self):
        cache.clear()
        self.password = 'Kulkas-Bersama-2026'
        self.user = User.objects.create_user('zombie', password=self.password)

    def attempt(self, password, username='zombie'):
        return self.client.post(reverse('main:login'), {'username': username, 'password': password})

    def test_locked_after_five_failures_even_with_correct_password(self):
        for _ in range(LoginThrottle.limit):
            self.assertEqual(self.attempt('salah').status_code, 200)
        response = self.attempt(self.password)
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'Terlalu banyak percobaan masuk', status_code=429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_username_is_case_insensitive_and_other_users_unaffected(self):
        for _ in range(LoginThrottle.limit):
            self.attempt('salah', username='ZOMBIE')
        self.assertEqual(self.attempt(self.password).status_code, 429)
        User.objects.create_user('necro', password=self.password)
        self.assertRedirects(self.attempt(self.password, username='necro'), reverse('main:show_main'))

    def test_successful_login_resets_counter(self):
        for _ in range(LoginThrottle.limit - 1):
            self.attempt('salah')
        self.assertRedirects(self.attempt(self.password), reverse('main:show_main'))
        self.client.post(reverse('main:logout'))
        for _ in range(LoginThrottle.limit - 1):
            self.attempt('salah')
        self.assertRedirects(self.attempt(self.password), reverse('main:show_main'))

    def test_blocked_for_without_expiry_marker_uses_full_window(self):
        request = RequestFactory().post('/login/')
        throttle = LoginThrottle(request, 'zombie')
        cache.set(throttle.key, LoginThrottle.limit)
        self.assertEqual(throttle.blocked_for(), LoginThrottle.window)


class RateLimitHelperTest(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def test_guests_are_limited_per_ip(self):
        view = rate_limit('test:guest', limit=1)(lambda request: HttpResponse('ok'))
        request = self.factory.post('/x/')
        request.user = AnonymousUser()
        self.assertEqual(view(request).status_code, 200)
        response = view(request)
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)

    def test_missing_ip_and_expired_key_are_handled(self):
        request = self.factory.post('/x/', REMOTE_ADDR='')
        self.assertEqual(client_ip(request), 'unknown')
        with patch('main.auth.cache.incr', side_effect=ValueError):
            view = rate_limit('test:expired', limit=1)(lambda request: HttpResponse('ok'))
            request.user = AnonymousUser()
            self.assertEqual(view(request).status_code, 200)
