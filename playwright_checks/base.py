"""Functional test dengan Playwright (browser Chromium sungguhan) untuk semua modul.

Menjalankan (dari root proyek):
    pip install -r playwright_checks/requirements.txt
    playwright install chromium                                   # sekali saja
    python manage.py test playwright_checks -p "check_*.py"       # semua pemeriksaan
    python manage.py test playwright_checks.check_graveyard -p "check_*.py"   # satu modul

Nama file memakai awalan check_ supaya `python manage.py test` biasa (pola test*.py)
dan coverage tim tidak ikut menjalankannya.

Test yang GAGAL = temuan (bug atau janji README yang belum ada). Tangkapan layar halaman
saat gagal tersimpan di playwright_checks/test-results/.
Lihat browsernya: set PLAYWRIGHT_HEADED=1 (PowerShell: $env:PLAYWRIGHT_HEADED=1).
"""
import os
import unittest
from pathlib import Path

from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

# API sync Playwright menjalankan event loop di thread test; tanpa ini Django menolak
# query ORM dari thread yang sama (SynchronousOnlyOperation).
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import expect, sync_playwright
except ImportError:  # paket belum di-install
    sync_playwright = None
    PlaywrightError = Exception
    expect = None

PASSWORD = 'Kulkas-Bersama-2026'
DESKTOP = {'width': 1280, 'height': 800}
MOBILE = {'width': 375, 'height': 812}
SMALL = {'width': 320, 'height': 640}
RESULTS_DIR = Path(__file__).resolve().parent / 'test-results'

# Payload XSS: bila ter-escape dengan benar, window.__pnXss tidak pernah terisi.
XSS = '<img src=x onerror="window.__pnXss=1">'

# Font Google tidak memengaruhi fungsi; dibalas kosong agar cepat dan tidak bergantung jaringan.
STUBBED_HOSTS = ('https://fonts.googleapis.com/', 'https://fonts.gstatic.com/')
TAILWIND_CDN = 'https://cdn.tailwindcss.com/'

# Pesan konsol yang wajar dan bukan bug aplikasi.
IGNORED_CONSOLE = (
    'cdn.tailwindcss.com should not be used in production',
)


class PlaywrightTestCase(StaticLiveServerTestCase):
    """Server Django sungguhan + Chromium untuk menguji alur seperti pengguna."""

    browser = None

    @classmethod
    def setUpClass(cls):
        if sync_playwright is None:
            raise unittest.SkipTest('playwright belum di-install: pip install -r playwright_checks/requirements.txt')
        super().setUpClass()
        cls._pw = sync_playwright().start()
        try:
            cls.browser = cls._pw.chromium.launch(headless=not os.environ.get('PLAYWRIGHT_HEADED'))
        except PlaywrightError as exc:
            cls._pw.stop()
            super().tearDownClass()
            raise unittest.SkipTest(f'Browser belum ada, jalankan: playwright install chromium ({exc})')

    @classmethod
    def tearDownClass(cls):
        if cls.browser:
            cls.browser.close()
            cls._pw.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.contexts = []
        self.problems = []  # galat JS / konsol / respons 5xx yang tertangkap selama test

    def tearDown(self):
        if self._has_failed():
            self._save_screenshots()
        for context in self.contexts:
            context.close()
        super().tearDown()

    def _has_failed(self):
        result = getattr(getattr(self, '_outcome', None), 'result', None)
        if result is None:
            return False
        # subTest yang gagal tercatat sebagai objek _SubTest dengan atribut test_case.
        return any(getattr(test, 'test_case', test) is self for test, _ in result.failures + result.errors)

    def _save_screenshots(self):
        RESULTS_DIR.mkdir(exist_ok=True)
        for c, context in enumerate(self.contexts):
            for p, page in enumerate(context.pages):
                try:
                    page.screenshot(path=RESULTS_DIR / f'{self.id()}-{c}-{p}.png', full_page=True)
                except PlaywrightError:
                    pass

    # ---------- Pengguna ----------
    def make_user(self, username='necro', password=PASSWORD):
        return User.objects.create_user(username, password=password)

    # ---------- Browser ----------
    def new_page(self, user=None, viewport=DESKTOP):
        """Tab baru dengan cookie terpisah. ``user`` diisi -> langsung dalam keadaan login."""
        context = self.browser.new_context(viewport=viewport, locale='id-ID', timezone_id='Asia/Jakarta')
        context.set_default_timeout(7000)
        self.contexts.append(context)
        self._route_externals(context)
        if user is not None:
            self.client.force_login(user)
            context.add_cookies([{
                'name': 'sessionid',
                'value': self.client.cookies['sessionid'].value,
                'url': self.live_server_url,
            }])
        page = context.new_page()
        page.on('pageerror', lambda exc: self.problems.append(f'JS error: {exc}'))
        page.on('console', self._on_console)
        page.on('response', self._on_response)
        page.on('dialog', lambda dialog: dialog.accept())  # confirm() hapus -> "OK"
        return page

    def _route_externals(self, context):
        for host in STUBBED_HOSTS:
            context.route(f'{host}**', lambda route: route.fulfill(status=200, content_type='text/css', body=''))
        # Opsional: jalankan tanpa internet dengan Tailwind hasil build lokal.
        shim = os.environ.get('PLAYWRIGHT_TAILWIND_JS')
        if shim:
            context.route(f'{TAILWIND_CDN}**', lambda route: route.fulfill(path=shim, content_type='text/javascript'))

    def _on_console(self, message):
        if message.type == 'error' and not any(text in message.text for text in IGNORED_CONSOLE):
            self.problems.append(f'console.error: {message.text}')

    def _on_response(self, response):
        if response.status >= 500 and response.url.startswith(self.live_server_url):
            self.problems.append(f'HTTP {response.status}: {response.url}')

    def url(self, path):
        return f'{self.live_server_url}{path}'

    def open(self, page, path, expected_status=200):
        response = page.goto(self.url(path))
        self.assertEqual(response.status, expected_status, f'{path} mengembalikan {response.status}')
        page.wait_for_load_state('load')
        self.wait_for_tailwind(page)
        return response

    def wait_for_tailwind(self, page):
        """CDN Tailwind membuat CSS setelah halaman dimuat; tunggu sampai kelas utilitas aktif
        (navbar ``flex``) supaya pengecekan tata letak tidak memeriksa halaman tanpa gaya."""
        try:
            page.wait_for_function(
                "() => { const el = document.querySelector('nav.pn-nav .pn-container');"
                " return !el || getComputedStyle(el).display === 'flex'; }",
                timeout=10000,
            )
        except PlaywrightError as exc:
            raise AssertionError('CSS Tailwind tidak termuat (cek koneksi ke cdn.tailwindcss.com)') from exc

    def login_via_form(self, page, username, password=PASSWORD):
        page.locator('input[name="username"]').fill(username)
        page.locator('input[name="password"]').fill(password)
        page.get_by_role('button', name='Masuk', exact=True).click()

    def fetch(self, page, path, method='GET', data=None, ajax=True):
        """Kirim request dari dalam halaman (cookie & CSRF ikut), kembalikan {status, body}."""
        return page.evaluate(
            """async ([url, method, data, ajax]) => {
                const headers = {};
                if (ajax) headers['X-Requested-With'] = 'XMLHttpRequest';
                const csrf = document.querySelector('input[name=csrfmiddlewaretoken]')
                    || { value: (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] };
                let body;
                if (method !== 'GET') {
                    body = new FormData();
                    body.append('csrfmiddlewaretoken', csrf.value || '');
                    Object.entries(data || {}).forEach(([k, v]) => body.append(k, v));
                }
                const r = await fetch(url, { method, body, headers, credentials: 'same-origin', redirect: 'manual' });
                const text = await r.text();
                let json = null;
                try { json = JSON.parse(text); } catch (_) {}
                return { status: r.status, json, text: text.slice(0, 500) };
            }""",
            [self.url(path), method, data, ajax],
        )

    # ---------- Pemeriksaan ----------
    def assert_no_problems(self):
        self.assertEqual(self.problems, [], 'Ada galat di browser:\n' + '\n'.join(self.problems))

    def horizontal_overflow(self, page):
        return page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')

    def assert_no_horizontal_scroll(self, page, label=''):
        overflow = self.horizontal_overflow(page)
        self.assertLessEqual(overflow, 0, f'{label or page.url}: halaman melebar {overflow}px (ada scroll horizontal)')

    def assert_no_xss(self, page, label=''):
        self.assertIsNone(page.evaluate('window.__pnXss'), f'{label or page.url}: payload XSS tereksekusi')

    def mark_page(self, page):
        """Tandai halaman; bila tanda hilang berarti halaman sempat dimuat ulang (bukan AJAX)."""
        page.evaluate('window.__pnNoReload = true')

    def assert_not_reloaded(self, page):
        self.assertTrue(page.evaluate('window.__pnNoReload === true'), 'Halaman dimuat ulang, seharusnya lewat AJAX')
