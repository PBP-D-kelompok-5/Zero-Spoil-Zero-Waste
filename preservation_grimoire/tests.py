from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from preservation_grimoire.models import PreservationGuide


class PreservationGrimoireViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='syarif', password='password123')
        
        self.guide = PreservationGuide.objects.create(
            author=self.user,
            title='Panduan Pengawetan Daging',
            category='MEAT',
            preservation_method='Freezing',
            content='Langkah-langkah pembekuan daging...',
            smell_indicator='Aroma segar vs asam/busuk',
            texture_indicator='Kenyal vs berlendir',
            visual_indicator='Warna merah segar vs pucat/kehijauan'
        )

    def test_grimoire_list_view(self):
        response = self.client.get(reverse('preservation_grimoire:grimoire_list'))
        self.assertEqual(response.status_code, 200)

    def test_grimoire_detail_view(self):
        response = self.client.get(reverse('preservation_grimoire:grimoire_detail', args=[self.guide.pk]))
        self.assertEqual(response.status_code, 200)

    def test_grimoire_create_view_get(self):
        self.client.login(username='syarif', password='password123')
        response = self.client.get(reverse('preservation_grimoire:grimoire_create'))
        self.assertEqual(response.status_code, 200)

    def test_grimoire_create_view_post(self):
        self.client.login(username='syarif', password='password123')
        response = self.client.post(reverse('preservation_grimoire:grimoire_create'), {
            'title': 'Panduan Pengawetan Sayur',
            'category': 'VEG',
            'preservation_method': 'Blanching',
            'content': 'Rebus sebentar lalu masukkan air es.',
            'smell_indicator': 'Aroma khas sayur segar',
            'texture_indicator': 'Renyah vs lembek',
            'visual_indicator': 'Hijau cerah vs kecokelatan'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PreservationGuide.objects.count(), 2)

    def test_grimoire_edit_view_get(self):
        self.client.login(username='syarif', password='password123')
        response = self.client.get(reverse('preservation_grimoire:grimoire_edit', args=[self.guide.pk]))
        self.assertEqual(response.status_code, 200)

    def test_grimoire_edit_view_post(self):
        self.client.login(username='syarif', password='password123')
        response = self.client.post(reverse('preservation_grimoire:grimoire_edit', args=[self.guide.pk]), {
            'title': 'Panduan Pengawetan Daging (Updated)',
            'category': 'MEAT',
            'preservation_method': 'Freezing & Vacuum',
            'content': 'Langkah-langkah pembekuan vakum...',
            'smell_indicator': 'Aroma segar',
            'texture_indicator': 'Kenyal',
            'visual_indicator': 'Merah segar'
        })
        self.assertEqual(response.status_code, 302)
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.title, 'Panduan Pengawetan Daging (Updated)')

    def test_grimoire_delete_view_post(self):
        self.client.login(username='syarif', password='password123')
        response = self.client.post(reverse('preservation_grimoire:grimoire_delete', args=[self.guide.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PreservationGuide.objects.count(), 0)

AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
GUIDE_DATA = {
    'title': 'Panduan Acar Timun',
    'category': 'VEG',
    'preservation_method': 'Pickling',
    'content': 'Rendam dalam larutan cuka.',
    'smell_indicator': 'Asam segar',
    'texture_indicator': 'Renyah',
    'visual_indicator': 'Hijau cerah',
}


class GrimoireAuthFlowTest(TestCase):
    """Alur autentikasi Grimoire mengikuti pola Death Clock (main/auth.py)."""

    def setUp(self):
        self.author = User.objects.create_user(username='syarif', password='password123')
        self.other = User.objects.create_user(username='tetangga', password='password123')
        self.guide = PreservationGuide.objects.create(author=self.author, **GUIDE_DATA)
        self.login_url = reverse('main:login')

    def url(self, name, *args):
        return reverse(f'preservation_grimoire:{name}', args=args)

    # ---------- Tamu ----------
    def test_guest_can_read_list_and_detail_with_login_cta(self):
        list_response = self.client.get(self.url('grimoire_list'))
        self.assertContains(list_response, f'{self.login_url}?next=')
        detail_response = self.client.get(self.url('grimoire_detail', self.guide.pk))
        self.assertContains(detail_response, f"{self.login_url}?next={self.url('grimoire_detail', self.guide.pk)}")

    def test_guest_is_redirected_to_login_with_next(self):
        for path in [self.url('grimoire_create'), self.url('grimoire_edit', self.guide.pk)]:
            self.assertRedirects(self.client.get(path), f'{self.login_url}?next={path}', fetch_redirect_response=False)

    def test_guest_ajax_gets_401_json(self):
        for path in [self.url('toggle_upvote', self.guide.pk), self.url('grimoire_delete', self.guide.pk)]:
            response = self.client.post(path, **AJAX)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['login_url'], self.login_url)
        self.assertTrue(PreservationGuide.objects.filter(pk=self.guide.pk).exists())

    # ---------- Kepemilikan ----------
    def test_other_users_get_404_on_edit_and_delete(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url('grimoire_edit', self.guide.pk)).status_code, 404)
        self.assertEqual(self.client.post(self.url('grimoire_delete', self.guide.pk)).status_code, 404)
        self.assertTrue(PreservationGuide.objects.filter(pk=self.guide.pk).exists())

    def test_staff_can_moderate(self):
        moderator = User.objects.create_user(username='mod', password='password123', is_staff=True)
        self.client.force_login(moderator)
        self.assertEqual(self.client.get(self.url('grimoire_edit', self.guide.pk)).status_code, 200)

    def test_delete_requires_post(self):
        self.client.force_login(self.author)
        self.assertEqual(self.client.get(self.url('grimoire_delete', self.guide.pk)).status_code, 405)
        self.assertTrue(PreservationGuide.objects.filter(pk=self.guide.pk).exists())

    def test_owner_sees_edit_and_delete_buttons_others_do_not(self):
        detail = self.url('grimoire_detail', self.guide.pk)
        self.client.force_login(self.author)
        self.assertContains(self.client.get(detail), self.url('grimoire_delete', self.guide.pk))
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(detail), self.url('grimoire_delete', self.guide.pk))

    # ---------- Aksi + pesan ----------
    def test_create_redirects_to_detail_with_message(self):
        self.client.force_login(self.author)
        response = self.client.post(self.url('grimoire_create'), {**GUIDE_DATA, 'title': 'Panduan Baru'}, follow=True)
        guide = PreservationGuide.objects.get(title='Panduan Baru')
        self.assertRedirects(response, self.url('grimoire_detail', guide.pk))
        self.assertContains(response, 'ditambahkan ke Grimoire')

    def test_ajax_delete_returns_json(self):
        self.client.force_login(self.author)
        response = self.client.post(self.url('grimoire_delete', self.guide.pk), **AJAX)
        self.assertEqual(response.json()['ok'], True)
        self.assertFalse(PreservationGuide.objects.exists())

    def test_upvote_ajax_toggles_and_plain_post_redirects(self):
        self.client.force_login(self.other)
        path = self.url('toggle_upvote', self.guide.pk)
        data = self.client.post(path, **AJAX).json()
        self.assertEqual((data['ok'], data['upvoted'], data['total_upvotes']), (True, True, 1))
        response = self.client.post(path)
        self.assertRedirects(response, self.url('grimoire_detail', self.guide.pk))
        self.assertEqual(self.guide.total_upvotes(), 0)

    def test_upvote_ignores_external_next(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url('toggle_upvote', self.guide.pk), {'next': 'https://contoh-jahat.com/'})
        self.assertRedirects(response, self.url('grimoire_detail', self.guide.pk))
