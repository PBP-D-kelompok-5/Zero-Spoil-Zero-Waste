from django.test import TestCase

from death_clock.forms import MAX_BULK_ITEMS, BulkAddForm, FilterForm, PantryItemForm, QuantityForm
from death_clock.models import Category, PantryItem, Storage, Unit
from death_clock.tests.helpers import days, make_item, make_user, today


def item_data(**overrides):
    data = {
        'name': '  Bayam  ',
        'category': Category.VEG,
        'quantity': 1,
        'unit': Unit.BUNCH,
        'storage': Storage.FRIDGE,
        'purchase_date': today().isoformat(),
        'expiry_date': '',
        'notes': '',
    }
    data.update(overrides)
    return data


class PantryItemFormTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def save(self, form):
        item = form.save(commit=False)
        item.user = self.user
        item.save()
        return item

    def test_blank_expiry_is_estimated(self):
        form = PantryItemForm(item_data())
        self.assertTrue(form.is_valid(), form.errors)
        item = self.save(form)
        self.assertEqual(item.name, 'Bayam')
        self.assertEqual(item.expiry_date, days(5))
        self.assertTrue(item.expiry_is_estimate)

    def test_explicit_expiry_is_not_estimate(self):
        form = PantryItemForm(item_data(expiry_date=days(2).isoformat()))
        self.assertTrue(form.is_valid(), form.errors)
        item = self.save(form)
        self.assertEqual(item.expiry_date, days(2))
        self.assertFalse(item.expiry_is_estimate)

    def test_expiry_before_purchase_is_rejected(self):
        form = PantryItemForm(item_data(purchase_date=days(-1).isoformat(), expiry_date=days(-3).isoformat()))
        self.assertFalse(form.is_valid())
        self.assertIn('expiry_date', form.errors)

    def test_future_purchase_date_is_rejected(self):
        form = PantryItemForm(item_data(purchase_date=days(1).isoformat()))
        self.assertFalse(form.is_valid())
        self.assertIn('purchase_date', form.errors)
        self.assertNotIn('expiry_date', form.errors)

    def test_quantity_must_be_positive(self):
        self.assertFalse(PantryItemForm(item_data(quantity=0)).is_valid())

    def test_edit_keeps_estimate_flag_only_when_date_unchanged(self):
        item = make_item(self.user, expires_in=5, expiry_is_estimate=True)
        same = PantryItemForm(item_data(purchase_date=item.purchase_date.isoformat(), expiry_date=item.expiry_date.isoformat(), quantity=3), instance=item)
        self.assertTrue(same.is_valid(), same.errors)
        self.assertTrue(same.save().expiry_is_estimate)

        changed = PantryItemForm(item_data(purchase_date=item.purchase_date.isoformat(), expiry_date=days(9).isoformat()), instance=item)
        self.assertTrue(changed.is_valid(), changed.errors)
        self.assertFalse(changed.save().expiry_is_estimate)

    def test_edit_with_blank_expiry_re_estimates_for_new_storage(self):
        item = make_item(self.user, expires_in=1, bought_ago=0)
        form = PantryItemForm(item_data(storage=Storage.FREEZER), instance=item)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().expiry_date, days(180))


class BulkAddFormTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def data(self, names, **overrides):
        data = {'names': names, 'category': Category.VEG, 'storage': Storage.FRIDGE, 'purchase_date': today().isoformat(), 'expiry_date': ''}
        data.update(overrides)
        return data

    def test_names_are_split_trimmed_and_deduplicated(self):
        form = BulkAddForm(self.data('bayam,  Bayam ,wortel\n tomat  ceri; ,'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['names'], ['bayam', 'wortel', 'tomat ceri'])

    def test_save_creates_items_with_estimate(self):
        form = BulkAddForm(self.data('bayam, wortel'))
        self.assertTrue(form.is_valid(), form.errors)
        form.save(self.user)
        items = PantryItem.objects.filter(user=self.user)
        self.assertEqual(items.count(), 2)
        self.assertTrue(all(item.expiry_is_estimate and item.expiry_date == days(5) for item in items))

    def test_save_with_shared_expiry(self):
        form = BulkAddForm(self.data('apel, jeruk', expiry_date=days(10).isoformat()))
        self.assertTrue(form.is_valid(), form.errors)
        form.save(self.user)
        self.assertFalse(PantryItem.objects.filter(expiry_is_estimate=True).exists())
        self.assertEqual(set(PantryItem.objects.values_list('expiry_date', flat=True)), {days(10)})

    def test_invalid_inputs(self):
        cases = {
            'empty': self.data(' , ;\n'),
            'too_many': self.data(', '.join(f'bahan {i}' for i in range(MAX_BULK_ITEMS + 1))),
            'too_long': self.data('x' * 101),
            'future_purchase': self.data('bayam', purchase_date=days(2).isoformat()),
            'expiry_before_purchase': self.data('bayam', expiry_date=days(-5).isoformat()),
        }
        for name, data in cases.items():
            with self.subTest(name):
                self.assertFalse(BulkAddForm(data).is_valid())


class SmallFormsTest(TestCase):
    def test_filter_form_ignores_unknown_values(self):
        values = FilterForm({'q': 'susu', 'status': 'ZOMBIE', 'category': 'DAIRY'}).values
        self.assertEqual(values, {'q': 'susu', 'status': '', 'category': 'DAIRY', 'storage': ''})

    def test_quantity_form(self):
        form = QuantityForm({'delta': '-1'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['delta'], -1)
        self.assertFalse(QuantityForm({'delta': '5'}).is_valid())
