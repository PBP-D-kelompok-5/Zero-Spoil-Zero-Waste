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