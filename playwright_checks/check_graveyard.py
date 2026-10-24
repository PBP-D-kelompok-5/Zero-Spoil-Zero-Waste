"""Modul 4 · The Graveyard & Waste Analytics (Adam)."""
import re
from decimal import Decimal

from death_clock.models import PantryItem
from death_clock.tests.helpers import make_item
from graveyard.models import GraveyardItem
from playwright_checks.base import MOBILE, XSS, PlaywrightTestCase, expect


def bury(user, name='Susu UHT', loss='18000', weight='1000', **extra):
    return GraveyardItem.objects.create(
        user=user, name=name, estimated_loss=Decimal(loss), weight_g=Decimal(weight), **extra
    )


class GraveyardCheck(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user('necro')

    def tile(self, page, label):
        return page.locator('.dc-tile', has_text=label)

    def test_tamu_melihat_halaman_pengenalan(self):
        page = self.new_page()
        self.open(page, '/graveyard/')
        expect(page.locator('#graveyard-items-count')).to_have_count(0)
        self.assert_no_problems()
        self.assertEqual(self.fetch(page, '/graveyard/json/')['status'], 401)

    def test_kubur_dari_death_clock(self):
        item = make_item(self.user, name='Bayam layu', expires_in=-2)
        page = self.new_page(user=self.user)
        self.open(page, '/death-clock/')
        page.locator(f'#dc-item-{item.pk}').get_by_role('link', name='Ke Graveyard').click()
        expect(page).to_have_url(re.compile(rf'/graveyard/move/{item.pk}/'))
        page.get_by_label('Alasan pembusukan atau pembuangan').select_option('FORGOTTEN')
        page.get_by_label('Estimasi kerugian (Rp)').fill('15000')
        page.get_by_label('Estimasi berat (gram)').fill('250')
        page.get_by_role('button', name='Konfirmasi Pemindahan ke Graveyard').click()

        expect(page).to_have_url(re.compile(r'/graveyard/$'))
        expect(page.locator('#graveyard-items-count')).to_have_text('(1)')
        expect(self.tile(page, 'Total Kerugian Uang')).to_contain_text('Rp 15.000')
        self.assertFalse(PantryItem.objects.filter(pk=item.pk).exists())
        buried = GraveyardItem.objects.get(user=self.user)
        self.assertEqual((buried.name, buried.reason, buried.estimated_loss), ('Bayam layu', 'FORGOTTEN', Decimal('15000')))
        self.assert_no_problems()

    def test_form_kubur_menolak_angka_tidak_valid(self):
        item = make_item(self.user, name='Tahu')
        page = self.new_page(user=self.user)
        self.open(page, f'/graveyard/move/{item.pk}/')
        page.get_by_label('Estimasi kerugian (Rp)').evaluate('el => el.removeAttribute("min")')  # lewati validasi browser
        page.get_by_label('Estimasi kerugian (Rp)').fill('-5000')
        page.get_by_role('button', name='Konfirmasi Pemindahan ke Graveyard').click()
        expect(page.locator('.pn-error').first).to_be_visible()
        expect(page.get_by_label('Estimasi kerugian (Rp)')).to_have_value('-5000')  # isian dipertahankan
        self.assertTrue(PantryItem.objects.filter(pk=item.pk).exists())
        self.assertFalse(GraveyardItem.objects.exists())

    def test_hapus_lewat_modal_ajax_tanpa_muat_ulang(self):
        bury(self.user, name='Susu UHT', loss='18000')
        keep = bury(self.user, name='Roti tawar', loss='12000')
        target = GraveyardItem.objects.get(name='Susu UHT')
        page = self.new_page(user=self.user)
        self.open(page, '/graveyard/')
        self.mark_page(page)
        page.locator(f'#graveyard-row-{target.pk}').get_by_role('button', name='Hapus').click()
        expect(page.locator('#reaper-modal')).to_have_class(re.compile('opacity-100'))
        expect(page.locator('#reaper-item-name')).to_have_text('Susu UHT')
        page.locator('#reaper-confirm-btn').click()

        expect(page.locator(f'#graveyard-row-{target.pk}')).to_have_count(0)
        expect(page.locator(f'#graveyard-card-{target.pk}')).to_have_count(0)
        expect(page.locator('#graveyard-items-count')).to_have_text('(1)')
        expect(page.locator('#graveyard-toast-message')).to_contain_text('Susu UHT')
        self.assert_not_reloaded(page)
        self.assertEqual(list(GraveyardItem.objects.values_list('pk', flat=True)), [keep.pk])
        self.assert_no_problems()

    def test_batal_hapus_tidak_menghapus(self):
        item = bury(self.user)
        page = self.new_page(user=self.user)
        self.open(page, '/graveyard/')
        page.locator(f'#graveyard-row-{item.pk}').get_by_role('button', name='Hapus').click()
        page.locator('#reaper-cancel-btn').click()
        expect(page.locator('#reaper-modal')).to_have_class(re.compile('opacity-0'))
        page.keyboard.press('Escape')
        self.assertTrue(GraveyardItem.objects.filter(pk=item.pk).exists())

    def test_analitik_ikut_diperbarui_setelah_hapus(self):
        """Temuan bila gagal: kartu total kerugian masih angka lama sampai halaman dimuat ulang."""
        bury(self.user, name='Susu UHT', loss='18000')
        bury(self.user, name='Roti tawar', loss='12000')
        target = GraveyardItem.objects.get(name='Susu UHT')
        page = self.new_page(user=self.user)
        self.open(page, '/graveyard/')
        expect(self.tile(page, 'Total Kerugian Uang')).to_contain_text('Rp 30.000')
        page.locator(f'#graveyard-row-{target.pk}').get_by_role('button', name='Hapus').click()
        page.locator('#reaper-confirm-btn').click()
        expect(page.locator(f'#graveyard-row-{target.pk}')).to_have_count(0)
        expect(self.tile(page, 'Total Kerugian Uang')).to_contain_text('Rp 12.000')

    def test_filter_kategori_alasan_dan_cari(self):
        bury(self.user, name='Susu UHT', category='DAIRY', reason='EXPIRED')
        bury(self.user, name='Bayam', category='VEG', reason='MOLD')
        page = self.new_page(user=self.user)
        self.open(page, '/graveyard/')
        page.locator('#category').select_option('DAIRY')
        page.get_by_role('button', name='Terapkan').click()
        expect(page.locator('#graveyard-items-count')).to_have_text('(1)')
        expect(page.locator('tbody')).to_contain_text('Susu UHT')

        self.open(page, '/graveyard/')
        page.locator('#reason').select_option('MOLD')
        page.locator('#q').fill('bay')
        page.get_by_role('button', name='Terapkan').click()
        expect(page.locator('tbody')).to_contain_text('Bayam')
        expect(page.locator('#graveyard-items-count')).to_have_text('(1)')

        self.open(page, '/graveyard/?q=tidakada')
        expect(page.get_by_text('Tidak ada bahan makanan yang sesuai')).to_be_visible()

    def test_wrapped_carousel_bisa_dikendalikan(self):
        for name in ('Susu UHT', 'Bayam', 'Roti'):
            bury(self.user, name=name)
        page = self.new_page(user=self.user)
        self.open(page, '/graveyard/')
        expect(page.locator('#haunting-wrapped-container')).to_be_visible()
        visible = page.locator('.wrapped-slide[aria-hidden="false"]')
        first = visible.get_attribute('data-slide-index')
        page.locator('#wrapped-next-btn').click()
        expect(visible).not_to_have_attribute('data-slide-index', first)
        page.locator('#wrapped-prev-btn').click()
        expect(visible).to_have_attribute('data-slide-index', first)
        page.locator('#wrapped-toggle-pause').click()
        expect(page.locator('#wrapped-pause-text')).to_have_text('Lanjut')
        self.assert_no_problems()

    def test_data_pengguna_lain_tidak_bocor(self):
        other = self.make_user('tetangga')
        theirs = bury(other, name='Rahasia Tetangga')
        their_pantry = make_item(other, name='Tahu Tetangga')
        page = self.new_page(user=self.user)
        self.open(page, '/graveyard/')
        expect(page.get_by_text('Rahasia Tetangga')).to_have_count(0)
        self.assertEqual(self.fetch(page, f'/graveyard/{theirs.pk}/delete/', 'POST')['status'], 404)
        self.open(page, f'/graveyard/move/{their_pantry.pk}/', expected_status=404)
        result = self.fetch(page, '/graveyard/json/')
        self.assertEqual(result['json']['count'], 0)
        self.assertTrue(GraveyardItem.objects.filter(pk=theirs.pk).exists())

    def test_nama_berbahaya_ter_escape(self):
        item = make_item(self.user, name=XSS, notes=XSS)
        bury(self.user, name=XSS, notes=XSS)
        page = self.new_page(user=self.user)
        self.open(page, f'/graveyard/move/{item.pk}/')
        self.assert_no_xss(page, 'form kubur')
        self.open(page, '/graveyard/')
        page.locator('.graveyard-delete-trigger').first.click()  # nama masuk ke modal lewat textContent
        self.assert_no_xss(page, 'daftar + modal')

    def test_tampilan_hp_memakai_kartu(self):
        bury(self.user, name='Susu UHT cokelat kemasan satu liter')
        page = self.new_page(user=self.user, viewport=MOBILE)
        self.open(page, '/graveyard/')
        expect(page.locator('table')).to_be_hidden()
        expect(page.locator('article[id^="graveyard-card-"]')).to_have_count(1)
        self.assert_no_horizontal_scroll(page, 'Graveyard (HP)')

    # ---------- Janji README yang belum ada (gagal = belum dikerjakan) ----------
    def test_readme_update_catatan_graveyard(self):
        """README: 'Update: Memperbarui data catatan pembuangan, harga beli, atau alasan pembuangan.'"""
        item = bury(self.user)
        page = self.new_page(user=self.user)
        self.open(page, '/graveyard/')
        row = page.locator(f'#graveyard-row-{item.pk}')
        expect(row.get_by_role('link', name=re.compile('ubah|edit', re.I))).to_have_count(1)

    def test_readme_filter_rentang_tanggal(self):
        """README: 'penyaringan data dinamis (HTMX/AJAX) berdasarkan rentang tanggal dan kategori'."""
        page = self.new_page(user=self.user)
        bury(self.user)
        self.open(page, '/graveyard/')
        expect(page.locator('form[role="search"] input[type="date"]')).to_have_count(2)
