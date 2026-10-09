from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from death_clock.models import PantryItem, Status
from death_clock.tests.helpers import make_item, make_user


class SeedCommandTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def run_seed(self, *args):
        out = StringIO()
        call_command('seed_death_clock', 'necro', *args, stdout=out)
        return out.getvalue()

    def test_seeds_fifty_items_with_every_status(self):
        output = self.run_seed('--seed', '7')
        items = PantryItem.objects.filter(user=self.user)
        self.assertEqual(items.count(), 50)
        self.assertIn('50 bahan ditambahkan', output)
        statuses = {item.status for item in items}
        self.assertTrue({Status.FLATLINING, Status.CRITICAL, Status.STABLE} <= statuses)
        self.assertTrue(all(item.expiry_date >= item.purchase_date for item in items))

    def test_clear_replaces_existing_items(self):
        make_item(self.user, 'Lama')
        self.run_seed('--count', '5', '--clear')
        self.assertEqual(PantryItem.objects.filter(user=self.user).count(), 5)
        self.assertFalse(PantryItem.objects.filter(name='Lama').exists())

    def test_rejects_unknown_user_and_bad_count(self):
        with self.assertRaises(CommandError):
            call_command('seed_death_clock', 'tidak-ada', stdout=StringIO())
        with self.assertRaises(CommandError):
            self.run_seed('--count', '0')
