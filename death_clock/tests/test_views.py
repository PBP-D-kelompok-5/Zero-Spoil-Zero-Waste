from pathlib import Path

from django.apps import apps
from django.urls import reverse

from death_clock.models import Category, PantryItem, Storage, Unit
from death_clock.tests.helpers import AJAX, DeathClockTestCase, days, make_item, make_user, today


def url(name, *args):
    return reverse(f'death_clock:{name}', args=args)


class GuestAccessTest(DeathClockTestCase):
    """Inventaris bersifat privat: tamu hanya melihat penjelasan modul."""

    def test_guest_sees_teaser_with_login_link(self):
        owner = make_user()
        make_item(owner, 'Rahasia kulkas')
        response = self.client.get(url('pantry_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'death_clock/guest.html')
        self.assertContains(response, f"{reverse('main:login')}?next=/death-clock/")
        self.assertNotContains(response, 'Rahasia kulkas')

    def test_guest_is_redirected_from_forms(self):
        response = self.client.get(url('item_create'))
        self.assertRedirects(response, f"{reverse('main:login')}?next={url('item_create')}")

    def test_guest_ajax_and_json_get_401(self):
        item = make_item(make_user())
        self.assertEqual(self.client.post(url('item_delete', item.pk), **AJAX).status_code, 401)
        for target in (url('pantry_json'), url('item_json', item.pk)):
            response = self.client.get(target)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['login_url'], reverse('main:login'))
        self.assertTrue(PantryItem.objects.filter(pk=item.pk).exists())


class ListViewTest(DeathClockTestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.flat = make_item(self.user, 'Bayam', expires_in=0)
        self.critical = make_item(self.user, 'Susu UHT', expires_in=2, category=Category.DAIRY)
        self.stable = make_item(self.user, 'Beras', expires_in=90, category=Category.GRAIN, storage=Storage.PANTRY, notes='karung kecil')
        self.saved = make_item(self.user, 'Tempe', expires_in=1, category=Category.MEAT)
        self.saved.resurrect()
        make_item(make_user('tetangga'), 'Punya orang lain')

    def names(self, response):
        return [item.name for item in response.context['items']]

    def test_lists_own_active_items_soonest_first(self):
        response = self.client.get(url('pantry_list'))
        self.assertTemplateUsed(response, 'death_clock/pantry_list.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertEqual(self.names(response), ['Bayam', 'Susu UHT', 'Beras'])
        self.assertNotContains(response, 'Punya orang lain')
        self.assertEqual(response.context['counts']['ACTIVE'], 3)
        self.assertContains(response, '<span data-dc-alert-count>1</span> bahan flatlining')

    def test_cards_link_active_items_to_graveyard(self):
        move_url = lambda item: reverse('graveyard:move_from_death_clock', args=[item.pk])
        self.assertContains(self.client.get(url('pantry_list')), move_url(self.flat))
        resurrected = self.client.get(f"{url('pantry_list')}?status=RESURRECTED")
        self.assertNotContains(resurrected, move_url(self.saved))

    def test_filters(self):
        cases = {
            'status=CRITICAL': ['Susu UHT'],
            'status=FLATLINING': ['Bayam'],
            'status=STABLE': ['Beras'],
            'status=RESURRECTED': ['Tempe'],
            'q=karung': ['Beras'],
            'q=susu': ['Susu UHT'],
            'category=GRAIN': ['Beras'],
            'storage=PANTRY': ['Beras'],
            'category=DAIRY&storage=PANTRY': [],
            'status=BOGUS': ['Bayam', 'Susu UHT', 'Beras'],
        }
        for query, expected in cases.items():
            with self.subTest(query):
                self.assertEqual(self.names(self.client.get(f"{url('pantry_list')}?{query}")), expected)

    def test_empty_states(self):
        self.assertContains(self.client.get(f"{url('pantry_list')}?q=zzz"), 'Tidak ada bahan yang cocok')
        PantryItem.objects.filter(pk=self.flat.pk).delete()
        self.assertContains(self.client.get(f"{url('pantry_list')}?status=FLATLINING"), 'Tidak ada yang flatlining')
        PantryItem.objects.filter(resurrected_at__isnull=True).delete()
        self.assertContains(self.client.get(url('pantry_list')), 'tidak ada yang terbuang')
        PantryItem.objects.all().delete()
        self.assertContains(self.client.get(url('pantry_list')), 'Kulkasmu masih sepi')

    def test_ajax_returns_list_fragment_and_counts(self):
        response = self.client.get(f"{url('pantry_list')}?status=CRITICAL", **AJAX)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['counts']['RESURRECTED'], 1)
        self.assertIn('Susu UHT', data['html'])
        self.assertNotIn('<html', data['html'])

    def test_json_endpoints(self):
        data = self.client.get(url('pantry_json')).json()
        self.assertEqual([item['name'] for item in data['items']], ['Bayam', 'Susu UHT', 'Beras'])
        self.assertEqual(data['count'], 3)
        self.assertEqual(self.client.get(f"{url('pantry_json')}?status=RESURRECTED").json()['items'][0]['name'], 'Tempe')

        detail = self.client.get(url('item_json', self.critical.pk)).json()
        self.assertEqual(detail['status'], 'CRITICAL')
        other = PantryItem.objects.get(name='Punya orang lain')
        self.assertEqual(self.client.get(url('item_json', other.pk)).status_code, 404)


class CreateViewTest(DeathClockTestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.data = {
            'name': 'Wortel', 'category': Category.VEG, 'quantity': 3, 'unit': Unit.PIECE,
            'storage': Storage.FRIDGE, 'purchase_date': today().isoformat(), 'expiry_date': '', 'notes': '',
        }

    def test_get_page_and_ajax_fragment(self):
        response = self.client.get(url('item_create'))
        self.assertTemplateUsed(response, 'death_clock/item_form_page.html')
        fragment = self.client.get(url('item_create'), **AJAX).json()
        self.assertTrue(fragment['ok'])
        self.assertIn('name="name"', fragment['html'])

    def test_create_regular_post(self):
        response = self.client.post(url('item_create'), self.data, follow=True)
        self.assertRedirects(response, url('pantry_list'))
        self.assertContains(response, 'Wortel masuk ke Death Clock.')
        item = PantryItem.objects.get()
        self.assertEqual((item.user, item.quantity, item.expiry_date), (self.user, 3, days(5)))

    def test_create_ajax(self):
        response = self.client.post(url('item_create'), self.data, **AJAX)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['item']['name'], 'Wortel')
        self.assertEqual(data['counts']['ACTIVE'], 1)
        self.assertIn('dc-item-', data['html'])

    def test_invalid_post(self):
        self.data['name'] = ''
        response = self.client.post(url('item_create'), self.data, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])
        self.assertIn('pn-error', response.json()['html'])
        self.assertEqual(self.client.post(url('item_create'), self.data).status_code, 200)
        self.assertFalse(PantryItem.objects.exists())

    def test_bulk_create(self):
        payload = {'names': 'bayam, kangkung, sawi', 'category': Category.VEG, 'storage': Storage.FRIDGE, 'purchase_date': today().isoformat()}
        self.assertTemplateUsed(self.client.get(url('item_bulk_create')), 'death_clock/item_form_page.html')
        response = self.client.post(url('item_bulk_create'), payload, **AJAX)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['counts']['ACTIVE'], 3)
        self.assertRedirects(self.client.post(url('item_bulk_create'), {**payload, 'names': 'tomat'}), url('pantry_list'))
        self.assertEqual(PantryItem.objects.filter(user=self.user).count(), 4)
        self.assertEqual(self.client.post(url('item_bulk_create'), {**payload, 'names': ''}, **AJAX).status_code, 400)


class ItemActionTest(DeathClockTestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.item = make_item(self.user, 'Telur ayam', expires_in=10, quantity=2, unit=Unit.EGG)
        self.other = make_item(make_user('tetangga'), 'Ayam tetangga')

    def test_update(self):
        self.assertTemplateUsed(self.client.get(url('item_update', self.item.pk)), 'death_clock/item_form_page.html')
        payload = {
            'name': 'Telur bebek', 'category': Category.MEAT, 'quantity': 6, 'unit': Unit.EGG, 'storage': Storage.FRIDGE,
            'purchase_date': self.item.purchase_date.isoformat(), 'expiry_date': days(14).isoformat(), 'notes': 'baru',
        }
        response = self.client.post(url('item_update', self.item.pk), payload, **AJAX)
        self.assertEqual(response.json()['item']['name'], 'Telur bebek')
        self.item.refresh_from_db()
        self.assertEqual((self.item.quantity, self.item.expiry_date), (6, days(14)))
        self.assertRedirects(self.client.post(url('item_update', self.item.pk), payload), url('pantry_list'))

    def test_quantity_steps_and_floor(self):
        response = self.client.post(url('item_quantity', self.item.pk), {'delta': '1'}, **AJAX)
        self.assertEqual(response.json()['item']['quantity'], 3)
        self.assertIn('<span data-dc-qty>3</span>', response.json()['html'])
        for _ in range(5):
            self.client.post(url('item_quantity', self.item.pk), {'delta': '-1'}, **AJAX)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 1)
        self.assertEqual(self.client.post(url('item_quantity', self.item.pk), {'delta': '10'}, **AJAX).status_code, 400)
        self.assertRedirects(self.client.post(url('item_quantity', self.item.pk), {'delta': '1'}), url('pantry_list'))
        self.assertEqual(self.client.get(url('item_quantity', self.item.pk)).status_code, 405)

    def test_resurrect_toggle(self):
        response = self.client.post(url('item_resurrect', self.item.pk), **AJAX)
        self.assertEqual(response.json()['item']['status'], 'RESURRECTED')
        self.assertEqual(response.json()['counts']['RESURRECTED'], 1)
        response = self.client.post(url('item_resurrect', self.item.pk), **AJAX)
        self.assertEqual(response.json()['item']['status'], 'STABLE')
        self.assertRedirects(self.client.post(url('item_resurrect', self.item.pk)), url('pantry_list'))

    def test_delete(self):
        self.assertEqual(self.client.get(url('item_delete', self.item.pk)).status_code, 405)
        response = self.client.post(url('item_delete', self.item.pk), **AJAX)
        self.assertEqual(response.json()['counts']['ACTIVE'], 0)
        self.assertFalse(PantryItem.objects.filter(pk=self.item.pk).exists())

        again = make_item(self.user, 'Roti')
        self.assertRedirects(self.client.post(url('item_delete', again.pk)), url('pantry_list'))

    def test_cannot_touch_other_users_items(self):
        for name in ('item_update', 'item_quantity', 'item_resurrect', 'item_delete'):
            with self.subTest(name):
                self.assertEqual(self.client.post(url(name, self.other.pk), {'delta': '1'}).status_code, 404)
        self.other.refresh_from_db()
        self.assertEqual((self.other.name, self.other.quantity, self.other.resurrected_at), ('Ayam tetangga', 1, None))


class IntegrationTest(DeathClockTestCase):
    def test_admin_changelist_shows_status(self):
        from django.contrib.auth.models import User
        admin = User.objects.create_superuser('admin', password='Admin-Kulkas-2026')
        make_item(admin, 'Kol', expires_in=0)
        self.client.force_login(admin)
        response = self.client.get(reverse('admin:death_clock_pantryitem_changelist'))
        self.assertContains(response, 'Flatlining')

    def test_navbar_and_landing_link_to_module(self):
        response = self.client.get(reverse('main:show_main'))
        self.assertContains(response, f'href="{url("pantry_list")}"', count=3)
        self.assertContains(response, 'Buka Death Clock')


class ModuleLayoutTest(DeathClockTestCase):
    """Template & static Death Clock hanya ada di templates/death_clock/ dan static/death_clock/ (folder utama).

    Salinan di dalam folder app membuat lokal dan PWS memakai file berbeda: template diambil dari
    folder utama, tetapi WhiteNoise di PWS menyajikan static dari folder app.
    """

    def test_no_templates_or_static_inside_app_folder(self):
        app_dir = Path(apps.get_app_config('death_clock').path)
        for folder in ('templates', 'static'):
            with self.subTest(folder):
                self.assertFalse(
                    (app_dir / folder).exists(),
                    f'Hapus death_clock/{folder}/; versi yang dipakai ada di {folder}/death_clock/.',
                )


class SeedDemoViewTest(DeathClockTestCase):
    """Tombol "Isi data contoh": hanya untuk inventaris kosong milik pengguna yang login."""

    def setUp(self):
        super().setUp()
        self.user = make_user()

    def test_guest_cannot_seed(self):
        self.assertRedirects(self.client.post(url('item_seed_demo')), f"{reverse('main:login')}?next={url('item_seed_demo')}")
        self.assertEqual(self.client.post(url('item_seed_demo'), **AJAX).status_code, 401)
        self.assertFalse(PantryItem.objects.exists())

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url('item_seed_demo')).status_code, 405)

    def test_empty_inventory_shows_button_and_seeds_fifty_items(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(url('pantry_list')), 'Isi 50 bahan contoh')
        response = self.client.post(url('item_seed_demo'), **AJAX)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('50 bahan contoh ditambahkan', data['message'])
        self.assertEqual(data['counts']['ACTIVE'] + data['counts']['RESURRECTED'], 50)
        self.assertEqual(data['counts']['RESURRECTED'], 5)
        self.assertNotContains(self.client.get(url('pantry_list')), 'bahan contoh')

    def test_non_empty_inventory_is_refused(self):
        self.client.force_login(self.user)
        make_item(self.user, 'Data asli')
        response = self.client.post(url('item_seed_demo'), **AJAX)
        self.assertEqual(response.status_code, 409)
        self.assertIn('masih kosong', response.json()['detail'])
        response = self.client.post(url('item_seed_demo'), follow=True)
        self.assertRedirects(response, url('pantry_list'))
        self.assertContains(response, 'masih kosong')
        self.assertEqual(PantryItem.objects.filter(user=self.user).count(), 1)

    def test_seed_is_per_user(self):
        other = make_user('tetangga')
        make_item(other, 'Punya tetangga')
        self.client.force_login(self.user)
        self.client.post(url('item_seed_demo'), **AJAX)
        self.assertEqual(PantryItem.objects.filter(user=other).count(), 1)
        self.assertEqual(PantryItem.objects.filter(user=self.user).count(), 50)


class RateLimitTest(DeathClockTestCase):
    """Endpoint yang mengubah data dibatasi per pengguna per menit (main.auth.rate_limit)."""

    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_login(self.user)
        self.bulk = {'names': 'bayam', 'category': Category.VEG, 'storage': Storage.FRIDGE, 'purchase_date': today().isoformat()}

    def test_bulk_add_limited_to_ten_per_minute(self):
        for _ in range(10):
            self.assertEqual(self.client.post(url('item_bulk_create'), self.bulk, **AJAX).status_code, 201)
        response = self.client.post(url('item_bulk_create'), self.bulk, **AJAX)
        self.assertEqual(response.status_code, 429)
        self.assertIn('Terlalu banyak permintaan', response.json()['detail'])
        self.assertGreater(int(response['Retry-After']), 0)
        page = self.client.post(url('item_bulk_create'), self.bulk)
        self.assertEqual(page.status_code, 429)
        self.assertTemplateUsed(page, '429.html')
        self.assertEqual(PantryItem.objects.filter(user=self.user).count(), 10)

    def test_get_requests_are_not_counted(self):
        for _ in range(12):
            self.assertEqual(self.client.get(url('item_bulk_create'), **AJAX).status_code, 200)
        self.assertEqual(self.client.post(url('item_bulk_create'), self.bulk, **AJAX).status_code, 201)

    def test_write_actions_share_sixty_per_minute(self):
        item = make_item(self.user)
        for _ in range(60):
            self.assertEqual(self.client.post(url('item_quantity', item.pk), {'delta': '1'}, **AJAX).status_code, 200)
        self.assertEqual(self.client.post(url('item_resurrect', item.pk), **AJAX).status_code, 429)
        item.refresh_from_db()
        self.assertEqual((item.quantity, item.resurrected_at), (61, None))

    def test_limit_is_per_user(self):
        for _ in range(11):
            self.client.post(url('item_bulk_create'), self.bulk, **AJAX)
        self.client.force_login(make_user('tetangga'))
        self.assertEqual(self.client.post(url('item_bulk_create'), self.bulk, **AJAX).status_code, 201)

    def test_seed_limited_to_three_per_minute(self):
        for _ in range(3):
            self.assertEqual(self.client.post(url('item_seed_demo'), **AJAX).status_code, 201)
            PantryItem.objects.filter(user=self.user).delete()
        self.assertEqual(self.client.post(url('item_seed_demo'), **AJAX).status_code, 429)
