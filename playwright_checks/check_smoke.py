"""Smoke test lintas modul: setiap halaman dibuka (desktop, HP 375 px, HP kecil 320 px;
tamu & pengguna) lalu dicek tidak 5xx, tidak ada galat JavaScript, dan tidak ada scroll horizontal.
Ditambah Dead Drop (Joshua) dan alur akun."""
from decimal import Decimal

from death_clock.tests.helpers import make_item
from graveyard.models import GraveyardItem
from playwright_checks.base import DESKTOP, MOBILE, SMALL, PlaywrightTestCase, expect
from preservation_grimoire.models import PreservationGuide
from recipe_alchemist.models import Recipe

GUEST_PAGES = [
    '/',
    '/login/',
    '/register/',
    '/death-clock/',
    '/recipes/',
    '/recipes/komunitas/',
    '/recipes/saya/',
    '/graveyard/',
    '/grimoire/',
]

USER_PAGES = [
    '/',
    '/death-clock/',
    '/death-clock/add/',
    '/death-clock/bulk-add/',
    '/recipes/',
    '/recipes/saya/',
    '/recipes/komunitas/',
    '/recipes/baru/',
    '/graveyard/',
    '/grimoire/',
    '/grimoire/create/',
]


class SiteSmokeTest(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user('necro')
        # Nama sengaja panjang: menguji kartu tidak melebarkan layar HP.
        self.pantry_item = make_item(self.user, name='Telur ayam kampung organik ukuran besar', expires_in=2)
        GraveyardItem.objects.create(
            user=self.user, name='Susu UHT cokelat kemasan satu liter', weight_g=Decimal('1000'),
            estimated_loss=Decimal('18000'),
        )
        self.guide = PreservationGuide.objects.create(
            author=self.user, title='Membekukan bayam tanpa jadi lembek', category='VEG',
            preservation_method='Freezing', content='Blansir 1 menit, tiriskan, bekukan.',
            smell_indicator='Bau apek', texture_indicator='Berlendir', visual_indicator='Bercak hitam',
        )
        self.recipe = Recipe.objects.create(
            user=self.user, title='Tumis bayam bawang putih', ingredients='bayam\nbawang putih',
            instructions='Tumis semua bahan.', is_public=True,
        )

    def detail_pages(self):
        return [f'/grimoire/{self.guide.pk}/', f'/recipes/{self.recipe.pk}/']

    def check_pages(self, pages, user=None):
        for viewport, label in ((DESKTOP, 'desktop'), (MOBILE, 'HP 375'), (SMALL, 'HP 320')):
            page = self.new_page(user=user, viewport=viewport)
            for path in pages:
                with self.subTest(path=path, layar=label, login=bool(user)):
                    self.open(page, path)
                    expect(page.locator('nav.pn-nav')).to_be_visible()
                    self.assert_no_horizontal_scroll(page, f'{path} ({label})')
        self.assert_no_problems()

    def test_halaman_tamu(self):
        self.check_pages(GUEST_PAGES + self.detail_pages())

    def test_halaman_pengguna(self):
        pages = USER_PAGES + self.detail_pages() + [
            f'/grimoire/{self.guide.pk}/edit/',
            f'/recipes/{self.recipe.pk}/ubah/',
            f'/graveyard/move/{self.pantry_item.pk}/',
        ]
        self.check_pages(pages, user=self.user)

    def test_halaman_404_memakai_template_sendiri(self):
        page = self.new_page()
        self.open(page, '/halaman-yang-tidak-ada/', expected_status=404)
        expect(page.locator('nav.pn-nav')).to_be_visible()  # templates/404.html extends base

    def test_menu_hp_bisa_dibuka_dan_menuju_modul(self):
        page = self.new_page(viewport=MOBILE)
        self.open(page, '/')
        menu = page.locator('#nav-mobile')
        expect(menu).to_be_hidden()
        page.get_by_role('button', name='Buka menu').click()
        expect(menu).to_be_visible()
        expect(page.get_by_role('button', name='Buka menu')).to_have_attribute('aria-expanded', 'true')
        menu.get_by_role('link', name='Preservation Grimoire').click()
        expect(page).to_have_url(self.url('/grimoire/'))
        self.assert_no_problems()

    def test_daftar_akun_baru_lalu_keluar(self):
        page = self.new_page()
        self.open(page, '/register/')
        page.locator('input[name="username"]').fill('necro_baru')
        page.locator('input[name="password1"]').fill('Kulkas-Bersama-2026')
        page.locator('input[name="password2"]').fill('Kulkas-Bersama-2026')
        page.locator('form.pn-form').get_by_role('button').click()
        expect(page.locator('nav.pn-nav')).to_contain_text('necro_baru')

        page.locator('nav.pn-nav').get_by_role('button', name='Keluar').first.click()
        expect(page.locator('nav.pn-nav').get_by_role('link', name='Masuk').first).to_be_visible()
        self.assert_no_problems()

    # ---------- Modul 3 · The Dead Drop (Joshua) ----------
    def test_dead_drop_punya_halaman(self):
        """README: papan berbagi surplus + peta OpenStreetMap. Gagal = modul belum ada."""
        page = self.new_page(user=self.user)
        self.open(page, '/')
        page.locator('nav.pn-nav').get_by_role('link', name='Dead Drop').click()
        page.wait_for_load_state('load')
        self.assertNotRegex(page.url, r'#dead-drop$', 'Menu Dead Drop masih menuju anchor di landing page, belum ada halaman modul')

    def test_login_salah_menampilkan_pesan(self):
        page = self.new_page()
        self.open(page, '/login/')
        self.login_via_form(page, 'necro', 'salah-sekali')
        expect(page.locator('.pn-alert[role="alert"]')).to_be_visible()
        expect(page).to_have_url(self.url('/login/'))

    def test_logout_hanya_lewat_post(self):
        page = self.new_page(user=self.user)
        self.open(page, '/')
        self.open(page, '/logout/', expected_status=405)
        self.open(page, '/')
        expect(page.locator('nav.pn-nav')).to_contain_text('necro')

    def test_next_ke_situs_lain_ditolak(self):
        page = self.new_page()
        self.open(page, '/login/?next=https://contoh-jahat.example/')
        self.login_via_form(page, 'necro')
        page.wait_for_load_state('load')
        self.assertTrue(page.url.startswith(self.live_server_url), f'diarahkan ke {page.url}')
