"""Tes endpoint DRF Death Clock untuk aplikasi Flutter (/api/death-clock/)."""
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from death_clock.models import Category, PantryItem, Status, Storage
from death_clock.tests.helpers import DeathClockTestCase, make_item, make_user

LIST_URL = reverse('death_clock_api:item-list')


def detail_url(pk):
    return reverse('death_clock_api:item-detail', args=[pk])


class DeathClockApiTestCase(DeathClockTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.other = make_user('tetangga')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def names(self, response):
        self.assertEqual(response.status_code, 200)
        return [item['name'] for item in response.json()]


class AccessTest(DeathClockApiTestCase):
    def test_guest_gets_403(self):
        item = make_item(self.user)
        guest = APIClient()
        for url in (LIST_URL, detail_url(item.pk)):
            response = guest.get(url)
            self.assertEqual(response.status_code, 403)
            self.assertIn('detail', response.json())

    def test_list_only_contains_own_items(self):
        make_item(self.user, name='Bayam Milikku')
        make_item(self.other, name='Tempe Tetangga')
        self.assertEqual(self.names(self.client.get(LIST_URL)), ['Bayam Milikku'])

    def test_detail_of_other_users_item_is_404(self):
        item = make_item(self.other)
        self.assertEqual(self.client.get(detail_url(item.pk)).status_code, 404)

    def test_detail_of_missing_item_is_404(self):
        self.assertEqual(self.client.get(detail_url(9999)).status_code, 404)

    def test_write_methods_not_allowed_yet(self):
        item = make_item(self.user)
        self.assertEqual(self.client.post(LIST_URL, {}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(detail_url(item.pk)).status_code, 405)


class PayloadTest(DeathClockApiTestCase):
    def test_detail_matches_legacy_to_dict(self):
        """Bentuk JSON API sama dengan endpoint /json/ lama, jadi model Dart cukup satu."""
        item = make_item(
            self.user, name='Susu UHT', expires_in=2, bought_ago=4,
            category=Category.DAIRY, quantity=2, unit='l', notes='Buka segel kemarin',
        )
        response = self.client.get(detail_url(item.pk))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        legacy = item.to_dict()

        self.assertEqual(set(data), set(legacy))
        datetime_fields = {'created_at', 'updated_at', 'resurrected_at'}
        for key in set(legacy) - datetime_fields:
            self.assertEqual(data[key], legacy[key], key)
        for key in datetime_fields - {'resurrected_at'}:
            self.assertEqual(parse_datetime(data[key]), parse_datetime(legacy[key]), key)
        self.assertIsNone(data['resurrected_at'])

    def test_computed_fields(self):
        item = make_item(self.user, name='Ayam', expires_in=1, bought_ago=1, category=Category.MEAT)
        data = self.client.get(detail_url(item.pk)).json()
        self.assertEqual(data['status'], Status.CRITICAL)
        self.assertEqual(data['status_label'], 'Critical')
        self.assertEqual(data['days_left'], 1)
        self.assertEqual(data['countdown_label'], 'Besok')
        self.assertEqual(data['life_percent'], 50)
        self.assertEqual(data['category_label'], 'Daging & Protein')
        self.assertIs(data['is_resurrected'], False)

    def test_resurrected_item(self):
        item = make_item(self.user, resurrected_at=timezone.now())
        data = self.client.get(detail_url(item.pk)).json()
        self.assertEqual(data['status'], Status.RESURRECTED)
        self.assertIs(data['is_resurrected'], True)
        self.assertIsNotNone(parse_datetime(data['resurrected_at']))


class FilterTest(DeathClockApiTestCase):
    def setUp(self):
        super().setUp()
        make_item(self.user, name='Tahu', expires_in=0)                     # Flatlining
        make_item(self.user, name='Bayam', expires_in=2)                    # Critical
        make_item(self.user, name='Beras', expires_in=60, category=Category.GRAIN,
                  storage=Storage.PANTRY, notes='karung 5 kg')              # Stable
        make_item(self.user, name='Kaldu', expires_in=30, storage=Storage.FREEZER,
                  resurrected_at=timezone.now())                            # Resurrected

    def test_default_lists_active_items_sorted_by_expiry(self):
        self.assertEqual(self.names(self.client.get(LIST_URL)), ['Tahu', 'Bayam', 'Beras'])

    def test_filter_by_status(self):
        expected = {
            'FLATLINING': ['Tahu'],
            'CRITICAL': ['Bayam'],
            'STABLE': ['Beras'],
            'RESURRECTED': ['Kaldu'],
        }
        for status, names in expected.items():
            self.assertEqual(self.names(self.client.get(LIST_URL, {'status': status})), names, status)

    def test_filter_by_category_and_storage(self):
        self.assertEqual(self.names(self.client.get(LIST_URL, {'category': 'GRAIN'})), ['Beras'])
        self.assertEqual(self.names(self.client.get(LIST_URL, {'storage': 'PANTRY'})), ['Beras'])
        self.assertEqual(
            self.names(self.client.get(LIST_URL, {'status': 'RESURRECTED', 'storage': 'FREEZER'})),
            ['Kaldu'],
        )

    def test_search_name_and_notes(self):
        self.assertEqual(self.names(self.client.get(LIST_URL, {'q': 'baya'})), ['Bayam'])
        self.assertEqual(self.names(self.client.get(LIST_URL, {'q': 'karung'})), ['Beras'])

    def test_empty_filter_values_are_ignored(self):
        response = self.client.get(LIST_URL, {'status': '', 'category': '', 'storage': '', 'q': ''})
        self.assertEqual(self.names(response), ['Tahu', 'Bayam', 'Beras'])

    def test_invalid_filter_returns_field_errors(self):
        response = self.client.get(LIST_URL, {'status': 'ZOMBIE', 'storage': 'GUDANG'})
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn('status', body)
        self.assertIn('storage', body)
        self.assertIsInstance(body['status'][0], str)

    def test_empty_inventory_returns_empty_list(self):
        PantryItem.objects.all().delete()
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


class SessionLoginFlowTest(DeathClockTestCase):
    """Alur yang sama dengan aplikasi Flutter: login lewat /api/auth/login/, lalu GET dengan cookie."""

    def test_list_after_api_login(self):
        user = make_user()
        make_item(user, name='Telur')
        client = APIClient(enforce_csrf_checks=True)
        login = client.post(
            reverse('auth_api:login'),
            {'username': 'necro', 'password': 'Kulkas-Bersama-2026'},
            format='json',
        )
        self.assertEqual(login.status_code, 200)
        response = client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['name'] for item in response.json()], ['Telur'])
