"""Modul 5 · Preservation Grimoire & Smell Test (Syarif)."""
import re

from playwright_checks.base import MOBILE, XSS, PlaywrightTestCase, expect
from preservation_grimoire.models import PreservationGuide


class GrimoireCheck(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.author = self.make_user('syarif')
        self.reader = self.make_user('necro')

    def guide(self, author=None, **extra):
        data = {
            'author': author or self.author, 'title': 'Membekukan bayam tanpa jadi lembek', 'category': 'VEG',
            'preservation_method': 'Freezing', 'content': 'Blansir 1 menit, tiriskan, bekukan.',
            'smell_indicator': 'Bau apek', 'texture_indicator': 'Berlendir', 'visual_indicator': 'Bercak hitam',
        }
        data.update(extra)
        return PreservationGuide.objects.create(**data)

    def fill_form(self, page, title):
        page.get_by_label('Judul panduan').fill(title)
        page.get_by_label('Kategori bahan').select_option('DAIRY')
        page.get_by_label('Metode pengawetan').fill('Pembekuan')
        page.get_by_label('Langkah pengawetan').fill('Bagi per porsi, bekukan maksimal 3 bulan.')
        page.get_by_label('Indikator aroma').fill('Masih layak: tawar / Rusak: asam')
        page.get_by_label('Indikator tekstur').fill('Rusak: menggumpal')
        page.get_by_label('Indikator tampilan').fill('Rusak: berubah kuning')

    def test_tamu_bisa_membaca_tapi_tidak_menulis(self):
        g = self.guide()
        page = self.new_page()
        self.open(page, '/grimoire/')
        page.get_by_role('heading', name=g.title).click()
        expect(page.get_by_role('heading', level=1)).to_have_text(g.title)
        expect(page.get_by_text('Bau apek')).to_be_visible()
        expect(page.get_by_role('link', name=re.compile('Masuk untuk upvote'))).to_be_visible()
        self.open(page, '/grimoire/create/')
        expect(page).to_have_url(re.compile(r'/login/\?next=%2Fgrimoire%2Fcreate%2F|/login/\?next=/grimoire/create/'))
        self.assert_no_problems()

    def test_crud_panduan_oleh_penulis(self):
        page = self.new_page(user=self.author)
        self.open(page, '/grimoire/')
        page.get_by_role('link', name='+ Tulis panduan').click()
        self.fill_form(page, 'Menyimpan susu sapi segar')
        page.locator('form.pn-form button[type="submit"]').click()
        expect(page.get_by_role('heading', level=1)).to_have_text('Menyimpan susu sapi segar')
        expect(page.get_by_text('Rusak: menggumpal')).to_be_visible()

        page.get_by_role('link', name='Ubah').click()
        expect(page.get_by_label('Judul panduan')).to_have_value('Menyimpan susu sapi segar')
        page.get_by_label('Judul panduan').fill('Menyimpan susu sapi segar di kulkas')
        page.locator('form.pn-form button[type="submit"]').click()
        expect(page.get_by_role('heading', level=1)).to_have_text('Menyimpan susu sapi segar di kulkas')

        page.get_by_role('button', name='Hapus').click()  # confirm() otomatis "OK"
        expect(page).to_have_url(re.compile(r'/grimoire/$'))
        self.assertFalse(PreservationGuide.objects.exists())
        self.assert_no_problems()

    def test_form_kosong_ditolak(self):
        page = self.new_page(user=self.author)
        self.open(page, '/grimoire/create/')
        page.locator('form.pn-form').evaluate('f => f.noValidate = true')
        page.locator('form.pn-form button[type="submit"]').click()
        expect(page.locator('.pn-error').first).to_be_visible()
        self.assertFalse(PreservationGuide.objects.exists())

    def test_upvote_ajax_bolak_balik(self):
        g = self.guide()
        page = self.new_page(user=self.reader)
        self.open(page, f'/grimoire/{g.pk}/')
        self.mark_page(page)
        button = page.locator('[data-grimoire-upvote] button')
        expect(button).to_have_attribute('aria-pressed', 'false')
        button.click()
        expect(page.locator('[data-upvote-count]')).to_have_text('1')
        expect(button).to_have_attribute('aria-pressed', 'true')
        button.click()
        expect(page.locator('[data-upvote-count]')).to_have_text('0')
        expect(button).to_have_attribute('aria-pressed', 'false')
        self.assert_not_reloaded(page)
        self.assertEqual(g.upvotes.count(), 0)
        self.assert_no_problems()

    def test_bukan_penulis_tidak_bisa_mengubah_atau_menghapus(self):
        g = self.guide()
        page = self.new_page(user=self.reader)
        self.open(page, f'/grimoire/{g.pk}/')
        expect(page.get_by_role('link', name='Ubah')).to_have_count(0)
        expect(page.get_by_role('button', name='Hapus')).to_have_count(0)
        self.open(page, f'/grimoire/{g.pk}/edit/', expected_status=404)
        self.open(page, f'/grimoire/{g.pk}/')
        self.assertEqual(self.fetch(page, f'/grimoire/{g.pk}/delete/', 'POST')['status'], 404)
        self.assertTrue(PreservationGuide.objects.filter(pk=g.pk).exists())

    def test_cari_dan_filter_kategori(self):
        self.guide(title='Membekukan bayam', category='VEG')
        self.guide(title='Mengawetkan keju', category='DAIRY', content='Bungkus kertas lilin.')
        page = self.new_page()
        self.open(page, '/grimoire/')
        page.locator('#grimoire-category').select_option('DAIRY')
        page.get_by_role('button', name='Cari').click()
        expect(page.get_by_role('heading', name='Mengawetkan keju')).to_be_visible()
        expect(page.get_by_role('heading', name='Membekukan bayam')).to_have_count(0)
        self.open(page, '/grimoire/?q=lilin')
        expect(page.get_by_role('heading', name='Mengawetkan keju')).to_be_visible()
        self.open(page, '/grimoire/?q=tidakada')
        expect(page.get_by_text('Belum ada panduan yang cocok')).to_be_visible()

    def test_teks_berbahaya_ter_escape(self):
        g = self.guide(title=XSS, preservation_method=XSS, content=XSS, smell_indicator=XSS,
                       texture_indicator=XSS, visual_indicator=XSS)
        page = self.new_page(user=self.author)
        for path in ('/grimoire/', f'/grimoire/{g.pk}/', f'/grimoire/{g.pk}/edit/'):
            self.open(page, path)
            self.assert_no_xss(page, path)

    def test_tampilan_hp(self):
        g = self.guide(title='Panduan sangat panjang untuk mengawetkan daging ayam kampung tanpa freezer burn')
        page = self.new_page(user=self.author, viewport=MOBILE)
        for path in ('/grimoire/', f'/grimoire/{g.pk}/', '/grimoire/create/'):
            with self.subTest(path=path):
                self.open(page, path)
                self.assert_no_horizontal_scroll(page, path)

    # ---------- Janji README / ketentuan tugas (gagal = belum dikerjakan) ----------
    def test_readme_cari_berdasarkan_metode_pengawetan(self):
        """README: 'pencarian dan pemfilteran instan berdasarkan kategori bahan dan metode pengawetan'."""
        self.guide(title='Acar timun', preservation_method='Pickling', content='Rendam cuka.')
        page = self.new_page()
        self.open(page, '/grimoire/?q=Pickling')
        expect(page.get_by_role('heading', name='Acar timun')).to_be_visible()

    def test_readme_pencarian_instan_tanpa_muat_ulang(self):
        self.guide(title='Membekukan bayam')
        self.guide(title='Mengawetkan keju', content='Bungkus kertas lilin.')
        page = self.new_page()
        self.open(page, '/grimoire/')
        self.mark_page(page)
        page.locator('#grimoire-q').fill('keju')  # tanpa menekan tombol Cari
        expect(page.get_by_role('heading', name='Membekukan bayam')).to_have_count(0)
        self.assert_not_reloaded(page)

    def test_ketentuan_endpoint_json(self):
        """midterm.pdf poin 2: data ditampilkan dalam HTML maupun JSON."""
        self.guide()
        page = self.new_page()
        self.open(page, '/grimoire/')
        result = self.fetch(page, '/grimoire/json/', ajax=False)
        self.assertEqual(result['status'], 200, 'Belum ada endpoint JSON panduan (dicoba /grimoire/json/)')
