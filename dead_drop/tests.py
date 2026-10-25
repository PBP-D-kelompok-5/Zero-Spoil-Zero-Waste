from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import FoodListing, ListingStatus
from .forms import FoodListingForm

# Create your tests here.
class FoodListingModelTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test_password")

        self.listing = FoodListing.objects.create(
            owner = self.owner,
            food_name = "Kangkung",
            description="Kangkung tersimpan dengan baik",
            pickup_location="Depok",
            pickup_time=timezone.now() + timedelta(days=1),
            pickup_notes="Temui saya di gerbang",
            latitude=Decimal("-6.200000"),
            longitude=Decimal("106.816666"),
        )

    def test_new_listing_defaults_to_available(self):
        listing = FoodListing.objects.get(pk=self.listing.pk)

        self.assertEqual(listing.status, ListingStatus.AVAILABLE)
        self.assertIsNone(listing.reserved_by)

    def test_string_representation_is_food_name(self):
        self.assertEqual(str(self.listing), "Kangkung")

class FoodListingFormTests(TestCase):
    def valid_form_data(self):
        data = {
            "food_name": "Kangkung",
            "description": "Kangkung tersimpan dengan baik",
            "pickup_location": "Depok",
            "pickup_time": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
            "pickup_notes": "Temui saya di gerbang",
            "latitude": "-6.200000",
            "longitude": "106.816666",
        }

        return data

    def test_accepts_valid_listing(self):
        form = FoodListingForm(data=self.valid_form_data())

        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_latitude_above_maximum(self):
        data = self.valid_form_data()
        data["latitude"] = "91"
        form = FoodListingForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("latitude", form.errors)

    def test_rejects_past_pickup_time(self):
        data = self.valid_form_data()
        data["pickup_time"] = (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        form = FoodListingForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("pickup_time", form.errors)

    def test_does_not_expose_server_managed_fields(self):
        form = FoodListingForm()
        self.assertNotIn("owner", form.fields)
        self.assertNotIn("reserved_by", form.fields)
        self.assertNotIn("status", form.fields)