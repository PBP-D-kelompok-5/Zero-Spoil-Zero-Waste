from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from urllib.parse import parse_qs, urlsplit

from .models import FoodListing, ListingStatus
from .forms import FoodListingForm

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

class FoodListingBoardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test_password")
        self.reserved_by = user_model.objects.create_user(username="reservationMaker", password="test_password")
        self.other_user = user_model.objects.create_user(username="otherUser", password="test_password")

        self.listing_available = FoodListing.objects.create(**self.valid_listing_data())

        reserved_data = self.valid_listing_data()
        reserved_data["reserved_by"] = self.reserved_by
        reserved_data["status"] = ListingStatus.RESERVED
        self.listing_reserved = FoodListing.objects.create(**reserved_data)

        claimed_data = self.valid_listing_data()
        claimed_data["reserved_by"] = self.reserved_by
        claimed_data["status"] = ListingStatus.CLAIMED
        claimed_data["claimed_at"] = timezone.now()
        self.listing_claimed = FoodListing.objects.create(**claimed_data)

    def valid_listing_data(self):
        data = {
            "owner": self.owner,
            "food_name": "Kangkung",
            "description": "Kangkung tersimpan dengan baik",
            "pickup_location": "Depok",
            "pickup_time": timezone.now() + timedelta(days=1),
            "pickup_notes": "Temui saya di gerbang",
            "latitude": Decimal("-6.200000"),
            "longitude": Decimal("106.816666"),
        }

        return data

    def test_anonymous_user_sees_available_listings_only(self):
        response = self.client.get(reverse("dead_drop:listing_board"))
        self.assertEqual(response.status_code, 200)

        available_ids = {listing.pk for listing in response.context["available_listings"]}
        self.assertIn(self.listing_available.pk, available_ids)
        self.assertEqual(list(response.context["reserved_listings"]), [])
        self.assertEqual(list(response.context["claimed_listings"]), [])

    def test_owner_can_see_reserved_and_claimed_listings(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("dead_drop:listing_board"))
        self.assertEqual(response.status_code, 200)

        reserved_ids = {
            listing.pk
            for listing in response.context["reserved_listings"]
        }
        claimed_ids = {
            listing.pk
            for listing in response.context["claimed_listings"]
        }

        self.assertIn(self.listing_reserved.pk, reserved_ids)
        self.assertIn(self.listing_claimed.pk, claimed_ids)

    def test_reservation_maker_can_see_reserved_and_claimed_listings(self):
        self.client.force_login(self.reserved_by)
        response = self.client.get(reverse("dead_drop:listing_board"))
        self.assertEqual(response.status_code, 200)

        reserved_ids = {
            listing.pk
            for listing in response.context["reserved_listings"]
        }
        claimed_ids = {
            listing.pk
            for listing in response.context["claimed_listings"]
        }

        self.assertIn(self.listing_reserved.pk, reserved_ids)
        self.assertIn(self.listing_claimed.pk, claimed_ids)

    def test_other_user_cannot_see_others_reserved_and_claimed_listings(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("dead_drop:listing_board"))
        self.assertEqual(response.status_code, 200)

        available_ids = [
            listing.pk
            for listing in response.context["available_listings"]
        ]
        reserved_ids = {
            listing.pk
            for listing in response.context["reserved_listings"]
        }
        claimed_ids = {
            listing.pk
            for listing in response.context["claimed_listings"]
        }

        self.assertIn(self.listing_available.pk, available_ids)
        self.assertNotIn(self.listing_reserved.pk, available_ids)
        self.assertNotIn(self.listing_claimed.pk, available_ids)
        self.assertNotIn(self.listing_reserved.pk, reserved_ids)
        self.assertNotIn(self.listing_claimed.pk, claimed_ids)

class FoodListingCreateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="test_password")
        self.create_url = reverse("dead_drop:create_listing")
        self.form_data = {
            "food_name": "Kangkung",
            "description": "Kangkung masih segar",
            "pickup_location": "Depok",
            "pickup_time": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
            "pickup_notes": "Temui saya di gerbang",
            "latitude": "-6.200000",
            "longitude": "106.816666",
        }

    def test_anonymous_user_redirected_to_login_page(self):
        response = self.client.get(self.create_url)
        expected_url = reverse("main:login")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response.url).path, expected_url)
        self.assertEqual(parse_qs(urlsplit(response.url).query).get("next"), [self.create_url])

    def test_logged_in_user_can_open_form(self):
        self.client.force_login(self.user)

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dead_drop/form.html")

    def test_valid_post_can_create_listing_with_available_status(self):
        self.client.force_login(self.user)
        response = self.client.post(self.create_url, data=self.form_data)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))
        self.assertEqual(FoodListing.objects.count(), 1)

        listing = FoodListing.objects.get()
        self.assertEqual(listing.self.owner, self.user)
        self.assertEqual(listing.status, ListingStatus.AVAILABLE)
        self.assertIsNone(listing.reserved_by)

    def test_invalid_post_cannot_create_listing(self):
        self.client.force_login(self.user)
        invalid_data = self.form_data.copy()
        invalid_data["food_name"] = ""

        response = self.client.post(self.create_url, data=invalid_data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("food_name", response.context["form"].errors)
        self.assertEqual(FoodListing.objects.count(), 0)