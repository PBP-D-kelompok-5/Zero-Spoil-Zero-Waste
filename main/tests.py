from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse


class MainPageTest(TestCase):
    def test_main_page_exists(self):
        response = self.client.get(reverse('main:show_main'))
        self.assertEqual(response.status_code, 200)

    def test_main_page_uses_base_template(self):
        response = self.client.get(reverse('main:show_main'))
        self.assertTemplateUsed(response, 'main/home.html')
        self.assertTemplateUsed(response, 'base.html')

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
