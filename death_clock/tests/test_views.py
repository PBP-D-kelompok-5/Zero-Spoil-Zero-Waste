from django.test import TestCase
from django.urls import reverse

from death_clock.models import Category, PantryItem, Storage, Unit
from death_clock.tests.helpers import AJAX, days, make_item, make_user, today


def url(name, *args):
    return reverse(f'death_clock:{name}', args=args)


class GuestAccessTest(TestCase):
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


class ListViewTest(TestCase):
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
        self.assertContains(response, '1 bahan flatlining')

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


class CreateViewTest(TestCase):
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


class ItemActionTest(TestCase):
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
        self.assertIn('3 <span', response.json()['html'])
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


class IntegrationTest(TestCase):
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
