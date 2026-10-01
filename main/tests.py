from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


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
