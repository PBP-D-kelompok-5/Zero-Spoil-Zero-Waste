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
        self.assertTemplateUsed(response, "dead_drop/food_listing_form.html")

    def test_valid_post_can_create_listing_with_available_status(self):
        self.client.force_login(self.user)
        response = self.client.post(self.create_url, data=self.form_data)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))
        self.assertEqual(FoodListing.objects.count(), 1)

        listing = FoodListing.objects.get()
        self.assertEqual(listing.owner, self.user)
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

class FoodListingReserveTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test_password")
        self.reserver = user_model.objects.create_user(username="reserver", password="test_password")
        self.other_user = user_model.objects.create_user(username="otherUser", password="test_password")

        self.listing = FoodListing.objects.create(
            owner=self.owner,
            food_name="Kangkung",
            description="Masih segar",
            pickup_location="Depok",
            pickup_time=timezone.now() + timedelta(days=1),
            pickup_notes="Temui saya di gerbang",
            latitude=Decimal("-6.200000"),
            longitude=Decimal("106.816666"),
        )

        self.reserve_url = reverse("dead_drop:reserve_listing", kwargs={"listing_id": self.listing.pk})

    def test_anonymous_user_redirected_to_login_page(self):
        response = self.client.get(self.reserve_url)
        expected_url = reverse("main:login")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response.url).path, expected_url)
        self.assertEqual(parse_qs(urlsplit(response.url).query).get("next"), [self.reserve_url])

    def test_get_request_is_not_allowed(self):
        self.client.force_login(self.reserver)

        response = self.client.get(self.reserve_url)

        self.assertEqual(response.status_code, 405)

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.AVAILABLE)
        self.assertIsNone(self.listing.reserved_by)

    def test_authenticated_user_can_reserve_available_listing(self):
        self.client.force_login(self.reserver)
        response = self.client.post(self.reserve_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.RESERVED)
        self.assertEqual(self.listing.reserved_by, self.reserver)

    def test_owner_cannot_reserve_own_listing(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.reserve_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.AVAILABLE)
        self.assertIsNone(self.listing.reserved_by)

    def test_user_cannot_reserve_reserved_listing(self):
        self.listing.status = ListingStatus.RESERVED
        self.listing.reserved_by = self.reserver
        self.listing.save()

        self.client.force_login(self.other_user)
        response = self.client.post(self.reserve_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.RESERVED)
        self.assertEqual(self.listing.reserved_by, self.reserver)

    def test_user_cannot_reserve_claimed_listing(self):
        self.listing.status = ListingStatus.CLAIMED
        self.listing.reserved_by = self.reserver
        self.listing.claimed_at = timezone.now()
        self.listing.save()

        self.client.force_login(self.other_user)
        response = self.client.post(self.reserve_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.CLAIMED)
        self.assertEqual(self.listing.reserved_by, self.reserver)

    def test_reservation_uses_logged_in_user_not_posted_reserver(self):
        self.client.force_login(self.reserver)

        response = self.client.post(self.reserve_url, data={"reserved_by": self.other_user.pk})

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.RESERVED)
        self.assertEqual(self.listing.reserved_by, self.reserver)

    def test_nonexistent_listing_returns_not_found(self):
        self.client.force_login(self.reserver)
        missing_url = reverse("dead_drop:reserve_listing", kwargs={"listing_id": self.listing.pk + 1})

        response = self.client.post(missing_url)

        self.assertEqual(response.status_code, 404)

class FoodListingCancelReservationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test_password")
        self.reserver = user_model.objects.create_user(username="reserver", password="test_password")
        self.other_user = user_model.objects.create_user(username="otherUser", password="test_password")

        self.listing = FoodListing.objects.create(
            owner=self.owner,
            food_name="Kangkung",
            description="Masih segar",
            pickup_location="Depok",
            pickup_time=timezone.now() + timedelta(days=1),
            pickup_notes="Temui saya di gerbang",
            latitude=Decimal("-6.200000"),
            longitude=Decimal("106.816666"),
            status= ListingStatus.RESERVED,
            reserved_by= self.reserver,
        )

        self.cancel_reserve_url = reverse("dead_drop:cancel_reserve_listing", kwargs={"listing_id": self.listing.pk})

    def test_anonymous_user_redirected_to_login_page(self):
        response = self.client.get(self.cancel_reserve_url)
        expected_url = reverse("main:login")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response.url).path, expected_url)
        self.assertEqual(parse_qs(urlsplit(response.url).query).get("next"), [self.cancel_reserve_url])

    def test_get_request_is_not_allowed(self):
        self.client.force_login(self.reserver)

        response = self.client.get(self.cancel_reserve_url)

        self.assertEqual(response.status_code, 405)

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.RESERVED)
        self.assertEqual(self.listing.reserved_by, self.reserver)

    def test_reserver_can_cancel_own_reservation(self):
        self.client.force_login(self.reserver)
        response = self.client.post(self.cancel_reserve_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.AVAILABLE)
        self.assertIsNone(self.listing.reserved_by)

    def test_owner_can_cancel_reservation(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.cancel_reserve_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.AVAILABLE)
        self.assertIsNone(self.listing.reserved_by)

    def test_other_user_cannot_cancel_reservation(self):
        self.client.force_login(self.other_user)
        response = self.client.post(self.cancel_reserve_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.RESERVED)
        self.assertEqual(self.listing.reserved_by, self.reserver)

    def test_owner_cannot_cancel_claimed_reservation(self):
        self.listing.status = ListingStatus.CLAIMED
        self.listing.claimed_at = timezone.now()
        self.listing.save()

        self.client.force_login(self.owner)
        response = self.client.post(self.cancel_reserve_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.CLAIMED)
        self.assertEqual(self.listing.reserved_by, self.reserver)

    def test_reserver_cannot_cancel_claimed_reservation(self):
        self.listing.status = ListingStatus.CLAIMED
        self.listing.claimed_at = timezone.now()
        self.listing.save()

        self.client.force_login(self.reserver)
        response = self.client.post(self.cancel_reserve_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.CLAIMED)
        self.assertEqual(self.listing.reserved_by, self.reserver)

    def test_nonexistent_listing_returns_not_found(self):
        self.client.force_login(self.reserver)
        missing_url = reverse("dead_drop:cancel_reserve_listing", kwargs={"listing_id": self.listing.pk + 1})

        response = self.client.post(missing_url)

        self.assertEqual(response.status_code, 404)

class FoodListingClaimTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test_password")
        self.reserver = user_model.objects.create_user(username="reservationMaker", password="test_password")
        self.other_user = user_model.objects.create_user(username="otherUser", password="test_password")

        self.listing_available = FoodListing.objects.create(**self.valid_listing_data())

        reserved_data = self.valid_listing_data()
        reserved_data["reserved_by"] = self.reserver
        reserved_data["status"] = ListingStatus.RESERVED
        self.listing_reserved = FoodListing.objects.create(**reserved_data)

        claimed_data = self.valid_listing_data()
        claimed_data["reserved_by"] = self.reserver
        claimed_data["status"] = ListingStatus.CLAIMED
        claimed_data["claimed_at"] = timezone.now()
        self.listing_claimed = FoodListing.objects.create(**claimed_data)

        self.claim_url = reverse("dead_drop:claim_listing", kwargs={"listing_id": self.listing_reserved.pk})

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

    def test_anonymous_user_redirected_to_login_page(self):
        response = self.client.get(self.claim_url)
        expected_url = reverse("main:login")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response.url).path, expected_url)
        self.assertEqual(parse_qs(urlsplit(response.url).query).get("next"), [self.claim_url])

    def test_get_request_is_not_allowed(self):
        self.client.force_login(self.reserver)

        response = self.client.get(self.claim_url)

        self.assertEqual(response.status_code, 405)

        self.listing_reserved.refresh_from_db()
        self.assertEqual(self.listing_reserved.status, ListingStatus.RESERVED)
        self.assertEqual(self.listing_reserved.reserved_by, self.reserver)

    def test_owner_can_mark_reserved_listing_as_claimed(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.claim_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing_reserved.refresh_from_db()
        self.assertEqual(self.listing_reserved.status, ListingStatus.CLAIMED)

    def test_claimed_listing_gets_claimed_at_timestamp(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.claim_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing_reserved.refresh_from_db()
        self.assertIsNotNone(self.listing_reserved.claimed_at)

    def test_reserver_cannot_mark_listing_as_claimed(self):
        self.client.force_login(self.reserver)
        response = self.client.post(self.claim_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing_reserved.refresh_from_db()
        self.assertEqual(self.listing_reserved.status, ListingStatus.RESERVED)
        self.assertIsNone(self.listing_reserved.claimed_at)

    def test_other_user_cannot_mark_listing_as_claimed(self):
        self.client.force_login(self.other_user)
        response = self.client.post(self.claim_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing_reserved.refresh_from_db()
        self.assertEqual(self.listing_reserved.status, ListingStatus.RESERVED)
        self.assertIsNone(self.listing_reserved.claimed_at)

    def test_owner_cannot_claim_available_listing(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("dead_drop:claim_listing", kwargs={"listing_id": self.listing_available.pk}))

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing_available.refresh_from_db()
        self.assertEqual(self.listing_available.status, ListingStatus.AVAILABLE)
        self.assertIsNone(self.listing_available.claimed_at)

    def test_owner_cannot_claim_claimed_listing(self):
        original_claimed_at = self.listing_claimed.claimed_at
        self.client.force_login(self.owner)
        response = self.client.post(reverse("dead_drop:claim_listing", kwargs={"listing_id": self.listing_claimed.pk}))

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing_claimed.refresh_from_db()
        self.assertEqual(self.listing_claimed.status, ListingStatus.CLAIMED)
        self.assertEqual(self.listing_claimed.claimed_at, original_claimed_at)

    def test_nonexistent_listing_returns_not_found(self):
        self.client.force_login(self.reserver)
        missing_url = reverse("dead_drop:claim_listing", kwargs={"listing_id": self.listing_claimed.pk + 1})

        response = self.client.post(missing_url)

        self.assertEqual(response.status_code, 404)

class FoodListingEditTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test_password")
        self.reserver = user_model.objects.create_user(username="reservationMaker", password="test_password")
        self.other_user = user_model.objects.create_user(username="otherUser", password="test_password")

        self.listing_available = FoodListing.objects.create(**self.valid_listing_data())

        claimed_data = self.valid_listing_data()
        claimed_data["reserved_by"] = self.reserver
        claimed_data["status"] = ListingStatus.CLAIMED
        claimed_data["claimed_at"] = timezone.now()
        self.listing_claimed = FoodListing.objects.create(**claimed_data)

        self.edit_url = reverse("dead_drop:edit_listing", kwargs={"listing_id": self.listing_available.pk})

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

    def edited_valid_listing_data(self):
        data = {
            "food_name": "Bayam",
            "description": "Bayam tersimpan dengan baik",
            "pickup_location": "Puncak",
            "pickup_time": timezone.now() + timedelta(days=2),
            "pickup_notes": "Temui saya di lapangan",
            "latitude": Decimal("6.200000"),
            "longitude": Decimal("-106.816666"),
        }

        return data

    def test_anonymous_user_redirected_to_login_page(self):
        response = self.client.get(self.edit_url)
        expected_url = reverse("main:login")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response.url).path, expected_url)
        self.assertEqual(parse_qs(urlsplit(response.url).query).get("next"), [self.edit_url])

    def test_owner_can_open_edit_form(self):
        self.client.force_login(self.owner)

        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dead_drop/food_listing_form.html")

    def test_owner_can_edit_listing(self):
        self.client.force_login(self.owner)
        edited_data = self.edited_valid_listing_data()
        response = self.client.post(self.edit_url, data=edited_data)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing_available.refresh_from_db()
        self.assertEqual(self.listing_available.food_name, edited_data["food_name"])
        self.assertEqual(self.listing_available.description, edited_data["description"])
        self.assertEqual(self.listing_available.pickup_location, edited_data["pickup_location"])
        self.assertEqual(self.listing_available.pickup_time, edited_data["pickup_time"])
        self.assertEqual(self.listing_available.pickup_notes, edited_data["pickup_notes"])
        self.assertEqual(self.listing_available.latitude, edited_data["latitude"])
        self.assertEqual(self.listing_available.longitude, edited_data["longitude"])

    def test_edit_preserves_status_and_reserver(self):
        reserved_data = self.valid_listing_data()
        reserved_data["status"] = ListingStatus.RESERVED
        reserved_data["reserved_by"] = self.reserver
        reserved_listing = FoodListing.objects.create(**reserved_data)

        edit_url = reverse("dead_drop:edit_listing", kwargs={"listing_id": reserved_listing.pk})

        self.client.force_login(self.owner)
        edited_data = self.edited_valid_listing_data()
        response = self.client.post(edit_url, data=edited_data)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        reserved_listing.refresh_from_db()
        self.assertEqual(reserved_listing.status, ListingStatus.RESERVED)
        self.assertEqual(reserved_listing.reserved_by, self.reserver)

    def test_invalid_edit_does_not_change_listing(self):
        self.client.force_login(self.owner)
        invalid_data = self.edited_valid_listing_data()
        invalid_data["pickup_time"] = (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")

        response = self.client.post(self.edit_url, data=invalid_data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("pickup_time", response.context["form"].errors)

        self.listing_available.refresh_from_db()
        self.assertEqual(self.listing_available.food_name, "Kangkung")
        self.assertEqual(self.listing_available.description, "Kangkung tersimpan dengan baik")

    def test_non_owner_cannot_edit_listing(self):
        original_values = {
            "food_name": self.listing_available.food_name,
            "description": self.listing_available.description,
            "pickup_location": self.listing_available.pickup_location,
            "pickup_time": self.listing_available.pickup_time,
            "pickup_notes": self.listing_available.pickup_notes,
            "latitude": self.listing_available.latitude,
            "longitude": self.listing_available.longitude,
            "status": self.listing_available.status,
            "reserved_by": self.listing_available.reserved_by,
        }

        self.client.force_login(self.other_user)
        edited_data = self.edited_valid_listing_data()
        response = self.client.post(self.edit_url, data=edited_data)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing_available.refresh_from_db()
        for field, original_value in original_values.items():
            with self.subTest(field=field):
                self.assertEqual(getattr(self.listing_available, field), original_value)

    def test_claimed_listing_cannot_be_edited(self):
        fields = (
            "food_name",
            "description",
            "pickup_location",
            "pickup_time",
            "pickup_notes",
            "latitude",
            "longitude",
            "status",
            "reserved_by",
            "claimed_at",
        )
        original_values = {
            field: getattr(self.listing_claimed, field)
            for field in fields
        }

        self.client.force_login(self.owner)
        edited_data = self.edited_valid_listing_data()
        response = self.client.post(reverse("dead_drop:edit_listing", kwargs={"listing_id": self.listing_claimed.pk}), data=edited_data)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))

        self.listing_claimed.refresh_from_db()
        for field, original_value in original_values.items():
            with self.subTest(field=field):
                self.assertEqual(getattr(self.listing_claimed, field), original_value)

    def test_nonexistent_listing_returns_not_found(self):
        self.client.force_login(self.owner)
        missing_url = reverse("dead_drop:edit_listing", kwargs={"listing_id": self.listing_claimed.pk + 1})

        response = self.client.post(missing_url)

        self.assertEqual(response.status_code, 404)

class FoodListingDeleteTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="test_password")
        self.reserver = user_model.objects.create_user(username="reservationMaker", password="test_password")
        self.other_user = user_model.objects.create_user(username="otherUser", password="test_password")

        self.listing_available = FoodListing.objects.create(**self.valid_listing_data())

        reserved_data = self.valid_listing_data()
        reserved_data["reserved_by"] = self.reserver
        reserved_data["status"] = ListingStatus.RESERVED
        self.listing_reserved = FoodListing.objects.create(**reserved_data)

        claimed_data = self.valid_listing_data()
        claimed_data["reserved_by"] = self.reserver
        claimed_data["status"] = ListingStatus.CLAIMED
        claimed_data["claimed_at"] = timezone.now()
        self.listing_claimed = FoodListing.objects.create(**claimed_data)

        self.delete_available_url = reverse("dead_drop:delete_listing", kwargs={"listing_id": self.listing_available.pk})
        self.delete_reserved_url = reverse("dead_drop:delete_listing", kwargs={"listing_id": self.listing_reserved.pk})
        self.delete_claimed_url = reverse("dead_drop:delete_listing", kwargs={"listing_id": self.listing_claimed.pk})

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

    def test_anonymous_user_redirected_to_login_page(self):
        response = self.client.get(self.delete_available_url)
        expected_url = reverse("main:login")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response.url).path, expected_url)
        self.assertEqual(parse_qs(urlsplit(response.url).query).get("next"), [self.delete_available_url])

    def test_get_request_is_not_allowed(self):
        self.client.force_login(self.reserver)

        response = self.client.get(self.delete_reserved_url)

        self.assertEqual(response.status_code, 405)

        self.listing_reserved.refresh_from_db()
        self.assertEqual(self.listing_reserved.status, ListingStatus.RESERVED)
        self.assertEqual(self.listing_reserved.reserved_by, self.reserver)

    def test_owner_can_delete_available_listing(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.delete_available_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))
        self.assertFalse(FoodListing.objects.filter(pk=self.listing_available.pk).exists())

    def test_non_owner_cannot_delete_listing(self):
        self.client.force_login(self.other_user)
        response = self.client.post(self.delete_available_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))
        self.assertFalse(FoodListing.objects.filter(pk=self.listing_available.pk).exists())

    def test_owner_cannot_delete_reserved_listing(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.delete_reserved_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))
        self.assertTrue(FoodListing.objects.filter(pk=self.listing_reserved.pk).exists())

    def test_owner_cannot_delete_claimed_listing(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.delete_claimed_url)

        self.assertRedirects(response, reverse("dead_drop:listing_board"))
        self.assertTrue(FoodListing.objects.filter(pk=self.listing_claimed.pk).exists())

    def test_nonexistent_listing_returns_not_found(self):
        self.client.force_login(self.owner)
        missing_url = reverse("dead_drop:delete_listing", kwargs={"listing_id": self.listing_claimed.pk + 1})

        response = self.client.post(missing_url)

        self.assertEqual(response.status_code, 404)