from django.test import TestCase

from death_clock.models import (
    CRITICAL_DAYS, Category, PantryItem, Status, Storage, estimate_expiry,
)
from death_clock.tests.helpers import days, make_item, make_user, today


class StatusTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_status_follows_days_left(self):
        cases = {
            -3: Status.FLATLINING,
            0: Status.FLATLINING,
            1: Status.CRITICAL,
            CRITICAL_DAYS: Status.CRITICAL,
            CRITICAL_DAYS + 1: Status.STABLE,
            30: Status.STABLE,
        }
        for expires_in, expected in cases.items():
            with self.subTest(expires_in=expires_in):
                item = make_item(self.user, expires_in=expires_in, bought_ago=10)
                self.assertEqual(item.days_left, expires_in)
                self.assertEqual(item.status, expected)

    def test_resurrected_overrides_expiry(self):
        item = make_item(self.user, expires_in=-5)
        item.resurrect()
        item.refresh_from_db()
        self.assertTrue(item.is_resurrected)
        self.assertEqual(item.status, Status.RESURRECTED)
        self.assertEqual(item.tone, 'hex')
        self.assertEqual(item.status_label, 'Resurrected')

        item.revive()
        item.refresh_from_db()
        self.assertFalse(item.is_resurrected)
        self.assertEqual(item.status, Status.FLATLINING)

    def test_tone_and_hint(self):
        item = make_item(self.user, expires_in=2)
        self.assertEqual(item.tone, 'ember')
        self.assertIn(str(CRITICAL_DAYS), item.status_hint)

    def test_countdown_label(self):
        labels = {-2: 'Lewat 2 hari', 0: 'Hari ini', 1: 'Besok', 5: '5 hari lagi'}
        for expires_in, label in labels.items():
            with self.subTest(expires_in=expires_in):
                self.assertEqual(make_item(self.user, expires_in=expires_in, bought_ago=10).countdown_label, label)

    def test_life_percent(self):
        self.assertEqual(make_item(self.user, expires_in=5, bought_ago=5).life_percent, 50)
        self.assertEqual(make_item(self.user, expires_in=0).life_percent, 0)
        self.assertEqual(make_item(self.user, expires_in=-4).life_percent, 0)
        # Data janggal (tanggal beli setelah kedaluwarsa) tidak membuat meter rusak.
        odd = make_item(self.user, expires_in=2, purchase_date=days(5))
        self.assertEqual(odd.life_percent, 100)

    def test_str(self):
        self.assertEqual(str(make_item(self.user, name='Tempe')), 'Tempe (necro)')


class QuerySetTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.flat = make_item(self.user, 'Bayam', expires_in=0)
        self.critical = make_item(self.user, 'Susu', expires_in=2)
        self.stable = make_item(self.user, 'Beras', expires_in=60)
        self.saved = make_item(self.user, 'Tahu', expires_in=1)
        self.saved.resurrect()

    def test_with_status_matches_property(self):
        qs = PantryItem.objects.filter(user=self.user)
        for status in Status.values:
            with self.subTest(status=status):
                expected = {item.pk for item in qs if item.status == status}
                self.assertEqual({item.pk for item in qs.with_status(status)}, expected)
        self.assertEqual(set(qs.with_status('')), {self.flat, self.critical, self.stable})

    def test_status_counts(self):
        counts = PantryItem.objects.filter(user=self.user).status_counts()
        self.assertEqual(counts, {'FLATLINING': 1, 'CRITICAL': 1, 'STABLE': 1, 'RESURRECTED': 1, 'ACTIVE': 3})

    def test_default_ordering_is_soonest_first(self):
        names = list(PantryItem.objects.active().values_list('name', flat=True))
        self.assertEqual(names, ['Bayam', 'Susu', 'Beras'])


class EstimateTest(TestCase):
    def test_estimate_uses_category_and_storage(self):
        self.assertEqual(estimate_expiry(Category.VEG, Storage.FRIDGE, today()), days(5))
        self.assertEqual(estimate_expiry(Category.MEAT, Storage.FREEZER, today()), days(90))
        self.assertEqual(estimate_expiry(Category.MEAT, Storage.PANTRY, today()), today())

    def test_unknown_values_fall_back(self):
        self.assertEqual(estimate_expiry('???', Storage.FRIDGE, today()), days(7))
        self.assertEqual(estimate_expiry(Category.VEG, '???', today()), days(7))


class ToDictTest(TestCase):
    def test_to_dict(self):
        user = make_user()
        item = make_item(user, 'Susu UHT', expires_in=2, category=Category.DAIRY, quantity=2, notes='rak atas')
        data = item.to_dict()
        self.assertEqual(data['id'], item.pk)
        self.assertEqual(data['name'], 'Susu UHT')
        self.assertEqual(data['category_label'], 'Produk Olahan Susu')
        self.assertEqual(data['quantity'], 2)
        self.assertEqual(data['status'], 'CRITICAL')
        self.assertEqual(data['days_left'], 2)
        self.assertEqual(data['expiry_date'], days(2).isoformat())
        self.assertIsNone(data['resurrected_at'])
        self.assertEqual(data['notes'], 'rak atas')

        item.resurrect()
        self.assertIsNotNone(item.to_dict()['resurrected_at'])
