"""Modul 2 · Recipe Alchemist (Nuno). Spoonacular dipalsukan (mock) agar tidak memakai kuota."""
import re
from unittest import mock

from death_clock.tests.helpers import make_item
from playwright_checks.base import MOBILE, XSS, PlaywrightTestCase, expect
from recipe_alchemist.models import Recipe
from recipe_alchemist.services import SpoonacularError

FAKE_RESULTS = [{
    'id': 716429, 'title': 'Pasta with Garlic and Spinach', 'image': '',
    'used': ['spinach'], 'missed': ['pasta', 'garlic'], 'ingredients': ['spinach', 'pasta', 'garlic'],
    'minutes': 25, 'diets': [], 'source_url': 'https://example.com/pasta',
}]


def spoonacular(results=None, error=None):
    side_effect = SpoonacularError(error) if error else None
    return mock.patch('recipe_alchemist.views.find_by_ingredients', return_value=results or [], side_effect=side_effect)


class RecipeAlchemistCheck(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user('necro')

    def recipe(self, user=None, **extra):
        data = {'user': user or self.user, 'title': 'Tumis bayam', 'ingredients': 'bayam\nbawang putih',
                'instructions': 'Tumis semua bahan.', 'is_public': True}
        data.update(extra)
        return Recipe.objects.create(**data)

    def search(self, page, ingredients):
        page.get_by_label('Bahan tambahan').fill(ingredients)
        page.get_by_role('button', name='Cari resep').click()
        page.wait_for_load_state('load')

    def test_tamu_mencari_lalu_diminta_masuk_untuk_menyimpan(self):
        page = self.new_page()
        self.open(page, '/recipes/')
        with spoonacular(FAKE_RESULTS) as fake:
            self.search(page, 'bayam')
        fake.assert_called_once()
        expect(page.get_by_role('heading', name='Dari Spoonacular')).to_be_visible()
        expect(page.get_by_role('heading', name='Pasta with Garlic and Spinach')).to_be_visible()
        page.get_by_role('link', name='Masuk untuk menyimpan').click()
        with spoonacular(FAKE_RESULTS):
            self.login_via_form(page, 'necro')
            expect(page).to_have_url(re.compile(r'/recipes/\?ingredients=bayam'))  # kembali ke hasil pencarian
            expect(page.get_by_role('button', name='Simpan resep')).to_be_visible()
        self.assert_no_problems()

    def test_simpan_resep_api_lewat_ajax(self):
        page = self.new_page(user=self.user)
        self.open(page, '/recipes/')
        with spoonacular(FAKE_RESULTS):
            self.search(page, 'bayam')
        self.mark_page(page)
        page.get_by_role('button', name='Simpan resep').click()
        expect(page.get_by_role('link', name='Tersimpan ✓ Lihat')).to_be_visible()
        self.assert_not_reloaded(page)
        saved = Recipe.objects.get(user=self.user)
        self.assertEqual((saved.spoonacular_id, saved.source), (716429, 'SPOONACULAR'))
        self.assertEqual(saved.ingredient_list, ['spinach', 'pasta', 'garlic'])

        # Cari lagi: sudah tersimpan, tidak bisa disimpan dua kali
        with spoonacular(FAKE_RESULTS):
            self.search(page, 'bayam')
        expect(page.get_by_text('Tersimpan', exact=True)).to_be_visible()
        self.open(page, '/recipes/saya/')
        expect(page.get_by_role('heading', name='Pasta with Garlic and Spinach')).to_be_visible()
        self.assert_no_problems()

    def test_galat_spoonacular_tampil_rapi_dan_hasil_lokal_tetap_ada(self):
        self.recipe(title='Tumis bayam bawang putih')
        page = self.new_page()
        self.open(page, '/recipes/')
        with spoonacular(error='Kuota harian Spoonacular habis. Coba lagi besok.'):
            self.search(page, 'bayam')
        expect(page.get_by_text('Kuota harian Spoonacular habis')).to_be_visible()
        expect(page.get_by_role('heading', name='Tumis bayam bawang putih')).to_be_visible()
        self.assert_no_problems()

    def test_pakai_bahan_dari_death_clock(self):
        make_item(self.user, name='bayam')
        self.recipe(title='Tumis bayam')
        page = self.new_page(user=self.user)
        self.open(page, '/recipes/')
        expect(page.get_by_label('Pakai bahan dari Death Clock')).to_be_checked()
        with spoonacular([]) as fake:
            self.search(page, '')
        self.assertIn('bayam', [n.strip() for n in fake.call_args.args[0]])
        expect(page.get_by_text('Cocok: bayam')).to_be_visible()

    def test_crud_resep_kustom(self):
        page = self.new_page(user=self.user)
        self.open(page, '/recipes/saya/')
        page.get_by_role('link', name='+ Resep baru').click()
        page.get_by_label('Judul resep').fill('Nasi goreng sisa sayur')
        page.get_by_label('Bahan').fill('1 piring nasi\nwortel\ntelur')
        page.get_by_label('Langkah memasak').fill('Tumis, masukkan nasi.')
        page.get_by_label('Waktu masak (menit)').fill('15')
        page.get_by_label('Catatan pribadi').fill('Pakai kecap manis')
        page.locator('form.pn-form button[type="submit"]').click()
        expect(page.get_by_role('heading', level=1)).to_have_text('Nasi goreng sisa sayur')
        expect(page.get_by_text('Pakai kecap manis')).to_be_visible()

        page.get_by_role('link', name='Ubah').click()
        page.get_by_label('Judul resep').fill('Nasi goreng spesial')
        page.locator('form.pn-form button[type="submit"]').click()
        expect(page.get_by_role('heading', level=1)).to_have_text('Nasi goreng spesial')

        page.get_by_role('button', name='Hapus').click()  # confirm() otomatis "OK"
        expect(page).to_have_url(re.compile(r'/recipes/saya/$'))
        self.assertFalse(Recipe.objects.exists())
        self.assert_no_problems()

    def test_form_resep_kosong_ditolak(self):
        page = self.new_page(user=self.user)
        self.open(page, '/recipes/baru/')
        page.locator('form.pn-form').evaluate('f => f.noValidate = true')
        page.locator('form.pn-form button[type="submit"]').click()
        expect(page.locator('.pn-error').first).to_be_visible()
        self.assertFalse(Recipe.objects.exists())

    def test_privasi_resep(self):
        other = self.make_user('tetangga')
        private = self.recipe(user=other, title='Resep rahasia', is_public=False)
        public = self.recipe(user=other, title='Resep umum', notes='catatan pribadi tetangga')
        page = self.new_page(user=self.user)
        self.open(page, '/recipes/komunitas/')
        expect(page.get_by_role('heading', name='Resep umum')).to_be_visible()
        expect(page.get_by_text('Resep rahasia')).to_have_count(0)
        self.open(page, f'/recipes/{private.pk}/', expected_status=404)
        self.open(page, f'/recipes/{public.pk}/')
        expect(page.get_by_text('catatan pribadi tetangga')).to_have_count(0)
        expect(page.get_by_role('link', name='Ubah')).to_have_count(0)
        self.open(page, f'/recipes/{public.pk}/ubah/', expected_status=404)
        self.assertEqual(self.fetch(page, f'/recipes/{public.pk}/hapus/', 'POST')['status'], 404)
        self.assertTrue(Recipe.objects.filter(pk=public.pk).exists())

    def test_cari_di_koleksi(self):
        self.recipe(title='Tumis bayam', is_public=False)
        self.recipe(title='Sup jagung', ingredients='jagung', is_public=False)
        page = self.new_page(user=self.user)
        self.open(page, '/recipes/saya/?q=jagung')
        expect(page.get_by_role('heading', name='Sup jagung')).to_be_visible()
        expect(page.get_by_role('heading', name='Tumis bayam')).to_have_count(0)

    def test_judul_berbahaya_ter_escape(self):
        r = self.recipe(title=XSS, ingredients=XSS, instructions=XSS, notes=XSS)
        page = self.new_page(user=self.user)
        for path in ('/recipes/komunitas/', '/recipes/saya/', f'/recipes/{r.pk}/', f'/recipes/{r.pk}/ubah/'):
            self.open(page, path)
            self.assert_no_xss(page, path)
        with spoonacular([{**FAKE_RESULTS[0], 'title': XSS}]):
            self.open(page, '/recipes/?ingredients=bayam')
        self.assert_no_xss(page, 'hasil Spoonacular')

    def test_tampilan_hp(self):
        self.recipe(title='Tumis bayam bawang putih dengan tahu goreng renyah')
        page = self.new_page(user=self.user, viewport=MOBILE)
        with spoonacular(FAKE_RESULTS):
            for path in ('/recipes/?ingredients=bayam', '/recipes/komunitas/', '/recipes/baru/'):
                with self.subTest(path=path):
                    self.open(page, path)
                    self.assert_no_horizontal_scroll(page, path)

    # ---------- Ketentuan tugas / README ----------
    def test_ketentuan_endpoint_json(self):
        """midterm.pdf poin 2: data ditampilkan dalam HTML maupun JSON (Death Clock: /death-clock/json/)."""
        self.recipe()
        page = self.new_page(user=self.user)
        self.open(page, '/recipes/')
        result = self.fetch(page, '/recipes/json/', ajax=False)
        self.assertEqual(result['status'], 200, 'Belum ada endpoint JSON resep (dicoba /recipes/json/)')
        self.assertIsNotNone(result['json'])
