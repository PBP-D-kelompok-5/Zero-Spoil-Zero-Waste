"""Modul 1 · Pantry Death Clock (Evan)."""
import re
from datetime import timedelta

from django.utils import timezone

from death_clock.models import PantryItem
from death_clock.tests.helpers import make_item
from playwright_checks.base import MOBILE, XSS, PlaywrightTestCase, expect


class DeathClockCheck(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user('necro')

    def dialog(self, page):
        return page.locator('#dc-dialog')

    def card(self, page, name):
        return page.locator('[data-dc-item]').filter(has=page.get_by_role('heading', name=name, exact=True))

    def open_add(self, page):
        page.locator('header').get_by_role('link', name='+ Tambah bahan').click()
        dialog = self.dialog(page)
        expect(dialog.get_by_label('Nama bahan')).to_be_visible()
        return dialog

    def test_tamu_diarahkan_masuk_lalu_kembali(self):
        page = self.new_page()
        self.open(page, '/death-clock/')
        expect(page.get_by_role('link', name='Masuk untuk mulai')).to_be_visible()
        self.open(page, '/death-clock/add/')
        expect(page).to_have_url(re.compile(r'/login/\?next='))
        self.login_via_form(page, 'necro')
        expect(page).to_have_url(re.compile(r'/death-clock/add/$'))
        expect(page.get_by_label('Nama bahan')).to_be_visible()
        self.assert_no_problems()

    def test_crud_lengkap_lewat_ajax_tanpa_muat_ulang(self):
        page = self.new_page(user=self.user)
        self.open(page, '/death-clock/')
        expect(page.get_by_text('Kulkasmu masih sepi')).to_be_visible()
        self.mark_page(page)

        # Create
        dialog = self.open_add(page)
        dialog.get_by_label('Nama bahan').fill('Bayam')
        dialog.get_by_label('Kategori').select_option('VEG')
        dialog.get_by_label('Perkiraan kedaluwarsa').fill((timezone.localdate() + timedelta(days=2)).isoformat())
        dialog.get_by_role('button', name='Simpan bahan').click()
        expect(dialog).to_be_hidden()
        expect(page.locator('#dc-toasts')).to_contain_text('Bayam masuk ke Death Clock.')
        card = self.card(page, 'Bayam')
        expect(card).to_contain_text('Critical')
        expect(page.locator('[data-dc-count="CRITICAL"]')).to_have_text('1')

        # Update jumlah: + lalu - ; tombol - mati di jumlah 1
        expect(card.get_by_role('button', name='Kurangi jumlah Bayam')).to_be_disabled()
        card.get_by_role('button', name='Tambah jumlah Bayam').click()
        expect(card.locator('.dc-stepper__value')).to_contain_text('2')
        card.get_by_role('button', name='Kurangi jumlah Bayam').click()
        expect(card.locator('.dc-stepper__value')).to_contain_text('1')

        # Update lewat modal
        card.get_by_role('link', name='Ubah').click()
        expect(dialog.get_by_label('Nama bahan')).to_have_value('Bayam')
        dialog.get_by_label('Nama bahan').fill('Bayam Merah')
        dialog.get_by_role('button', name='Simpan perubahan').click()
        expect(dialog).to_be_hidden()
        card = self.card(page, 'Bayam Merah')
        expect(card).to_be_visible()

        # Filter cari & kotak status
        page.get_by_label('Cari').fill('wortel')
        expect(page.get_by_text('Tidak ada bahan yang cocok')).to_be_visible()
        page.get_by_label('Cari').fill('')
        expect(card).to_be_visible()
        page.locator('[data-dc-status="STABLE"]').click()
        expect(card).to_have_count(0)
        page.locator('[data-dc-status="STABLE"]').click()  # klik lagi = lepas filter
        expect(card).to_be_visible()

        # Resurrect, lalu kembalikan, lalu resurrect lagi
        card.get_by_role('button', name='✓ Sudah diolah').click()
        expect(page.locator('[data-dc-count="RESURRECTED"]')).to_have_text('1')
        page.locator('[data-dc-status="RESURRECTED"]').click()
        card = self.card(page, 'Bayam Merah')
        card.get_by_role('button', name='Kembalikan').click()
        expect(page.locator('[data-dc-count="RESURRECTED"]')).to_have_text('0')
        expect(page.locator('[data-dc-count="CRITICAL"]')).to_have_text('1')

        # Delete dua langkah
        page.get_by_role('link', name='Reset').click()
        card = self.card(page, 'Bayam Merah')
        delete = card.get_by_role('button', name='Hapus Bayam Merah')
        delete.click()
        expect(delete).to_have_text('Yakin hapus?')
        delete.click()
        expect(card).to_have_count(0)
        expect(page.locator('[data-dc-count="CRITICAL"]')).to_have_text('0')

        self.assert_not_reloaded(page)
        self.assertFalse(PantryItem.objects.filter(user=self.user).exists())
        self.assert_no_problems()

    def test_tambah_massal(self):
        page = self.new_page(user=self.user)
        self.open(page, '/death-clock/')
        page.locator('header').get_by_role('link', name='Tambah massal').click()
        dialog = self.dialog(page)
        dialog.get_by_label('Daftar bahan').fill('wortel, tomat\nkangkung, Wortel')
        dialog.get_by_role('button', name='Tambahkan semua').click()
        expect(page.locator('#dc-toasts')).to_contain_text('3 bahan masuk ke Death Clock.')  # duplikat dibuang
        expect(page.locator('[data-dc-item]')).to_have_count(3)
        self.assert_no_problems()

    def test_form_tidak_valid_tampil_di_modal(self):
        page = self.new_page(user=self.user)
        self.open(page, '/death-clock/')
        dialog = self.open_add(page)
        dialog.get_by_label('Tanggal beli').fill((timezone.localdate() + timedelta(days=3)).isoformat())
        dialog.get_by_role('button', name='Simpan bahan').click()
        expect(dialog).to_be_visible()
        expect(dialog.locator('.pn-error')).to_contain_text(['Tanggal beli tidak boleh di masa depan.'])
        self.assertEqual(PantryItem.objects.count(), 0)

    def test_label_modal_terhubung_ke_field_modal(self):
        """Regresi: dulu id form filter (id_category) bentrok dengan id field di modal."""
        page = self.new_page(user=self.user)
        self.open(page, '/death-clock/')
        dialog = self.open_add(page)
        dialog.locator('label', has_text='Kategori').click()
        self.assertTrue(dialog.get_by_label('Kategori').evaluate('el => el === document.activeElement'))
        duplicates = page.evaluate(
            "[...document.querySelectorAll('[id]')].map(e => e.id).filter((id, i, all) => all.indexOf(id) !== i)"
        )
        self.assertEqual(duplicates, [], f'id ganda di halaman: {duplicates}')

    def test_data_pengguna_lain_tidak_bocor(self):
        other = self.make_user('tetangga')
        item = make_item(other, name='Susu Tetangga')
        page = self.new_page(user=self.user)
        self.open(page, f'/death-clock/{item.pk}/edit/', expected_status=404)
        self.open(page, '/death-clock/')
        expect(page.get_by_text('Susu Tetangga')).to_have_count(0)
        for path, method in ((f'/death-clock/{item.pk}/delete/', 'POST'), (f'/death-clock/json/{item.pk}/', 'GET')):
            with self.subTest(path=path):
                self.assertEqual(self.fetch(page, path, method)['status'], 404)
        self.assertTrue(PantryItem.objects.filter(pk=item.pk).exists())

    def test_endpoint_json(self):
        make_item(self.user, name='Bayam')
        make_item(self.make_user('tetangga'), name='Tahu')
        guest = self.new_page()
        self.open(guest, '/')
        self.assertEqual(self.fetch(guest, '/death-clock/json/')['status'], 401)
        page = self.new_page(user=self.user)
        self.open(page, '/death-clock/')
        result = self.fetch(page, '/death-clock/json/')
        self.assertEqual(result['status'], 200)
        self.assertEqual([i['name'] for i in result['json']['items']], ['Bayam'])

    def test_nama_berbahaya_ter_escape(self):
        page = self.new_page(user=self.user)
        self.open(page, '/death-clock/')
        dialog = self.open_add(page)
        dialog.get_by_label('Nama bahan').fill(XSS)
        dialog.get_by_label('Catatan (opsional)').fill(XSS)
        dialog.get_by_role('button', name='Simpan bahan').click()
        expect(page.locator('[data-dc-item]')).to_have_count(1)  # kartu dari AJAX
        self.assert_no_xss(page, 'kartu AJAX')
        self.open(page, '/death-clock/')
        self.assert_no_xss(page, 'daftar')

    def test_tampilan_hp(self):
        for name, days_left in (('Telur ayam kampung organik ukuran besar', 10), ('Susu UHT', 1), ('Bayam', -1)):
            make_item(self.user, name=name, expires_in=days_left, bought_ago=3)
        page = self.new_page(user=self.user, viewport=MOBILE)
        self.open(page, '/death-clock/')
        expect(page.locator('[data-dc-item]')).to_have_count(3)
        self.assert_no_horizontal_scroll(page, 'Death Clock (HP)')
        dialog = self.open_add(page)
        self.assert_no_horizontal_scroll(page, 'Death Clock modal (HP)')
        dialog.get_by_role('button', name='Tutup').click()
        expect(dialog).to_be_hidden()
        self.assert_no_problems()
