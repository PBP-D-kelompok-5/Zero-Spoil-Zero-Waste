from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import GrimoireItem 
class GrimoireViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.item = GrimoireItem.objects.create(
            title='Cara Mengawetkan Daging',
            content='Langkah-langkah pengawetan...',
            category='Daging'
        )

    def test_grimoire_list_view(self):
        response = self.client.get(reverse('preservation_grimoire:grimoire_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'preservation_grimoire/grimoire_list.html')

    def test_grimoire_detail_view(self):
        response = self.client.get(reverse('preservation_grimoire:grimoire_detail', args=[self.item.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'preservation_grimoire/grimoire_detail.html')

    def test_grimoire_create_view(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('preservation_grimoire:grimoire_create'), {
            'title': 'Cara Mengeringkan Buah',
            'content': 'Gunakan oven...',
            'category': 'Buah'
        })
        self.assertEqual(response.status_code, 302) # Redirect setelah berhasil buat

    def test_grimoire_update_view(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('preservation_grimoire:grimoire_edit', args=[self.item.pk]), {
            'title': 'Cara Mengawetkan Daging (Updated)',
            'content': 'Konten diperbarui...',
            'category': 'Daging'
        })
        self.assertEqual(response.status_code, 302)

