import hashlib
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse

from .forms import FoodListingForm
from .models import FoodListing, ListingStatus

def visible_listing_for(user):
    queryset = FoodListing.objects.all()

    if not user.is_authenticated:
        return queryset.filter(status=ListingStatus.AVAILABLE)

    return queryset.filter(
        Q(status=ListingStatus.AVAILABLE)
        | (
            Q(status__in=(ListingStatus.RESERVED, ListingStatus.CLAIMED))
            & (Q(owner=user) | Q(reserved_by=user))
        )
    )

def listing_board_context(user, message="", success=None):
    queryset = visible_listing_for(user).select_related("owner", "reserved_by")
    available_listings = queryset.filter(status=ListingStatus.AVAILABLE)
    reserved_listings = queryset.filter(status=ListingStatus.RESERVED)
    claimed_listings = queryset.filter(status=ListingStatus.CLAIMED)

    map_listings = list(available_listings) + list(reserved_listings)
    map_markers = [
        {
            "listing_id": listing.pk,
            "food_name": listing.food_name,
            "pickup_location": listing.pickup_location,
            "latitude": float(listing.latitude),
            "longitude": float(listing.longitude),
            "status": listing.status,
        }
        for listing in map_listings
    ]

    return {
        "available_listings": available_listings,
        "reserved_listings": reserved_listings,
        "claimed_listings": claimed_listings,
        "map_markers": map_markers,
        "board_message": message,
        "board_success": success,
    }


def render_htmx_board(request, message, success):
    return render(
        request,
        "dead_drop/partials/listing_board_content.html",
        listing_board_context(request.user, message, success),
    )


def listing_board(request):
    return render(
        request,
        "dead_drop/listing_board.html",
        listing_board_context(request.user),
    )

@login_required
@require_GET
def geocode_location(request):
    query = " ".join(request.GET.get("q", "").split())

    if not query:
        return JsonResponse(
            {"error": "Masukkan alamat atau nama lokasi."},
            status=400,
        )

    if len(query) > 200:
        return JsonResponse(
            {"error": "Pencarian lokasi maksimal 200 karakter."},
            status=400,
        )

    normalized_query = query.casefold()
    query_hash = hashlib.sha256(
        normalized_query.encode("utf-8")
    ).hexdigest()
    cache_key = f"dead_drop:nominatim:{query_hash}"

    cached_result = cache.get(cache_key)

    if cached_result == {"not_found": True}:
        return JsonResponse(
            {"error": "Lokasi tidak ditemukan."},
            status=404,
        )

    if cached_result is not None:
        return JsonResponse(cached_result)

    # Hanya izinkan maksimal satu permintaan yang belum tercache per detik.
    if not cache.add("dead_drop:nominatim:request_lock", True, timeout=1):
        return JsonResponse(
            {"error": "Tunggu sebentar sebelum mencari lokasi lain."},
            status=429,
        )

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "id",
            },
            headers={
                "User-Agent": settings.NOMINATIM_USER_AGENT,
                "Accept-Language": "id",
            },
            timeout=5,
        )
        response.raise_for_status()
        results = response.json()
    except (requests.RequestException, ValueError):
        return JsonResponse(
            {"error": "Layanan pencarian lokasi sedang tidak tersedia."},
            status=503,
        )

    if not results:
        cache.set(cache_key, {"not_found": True}, timeout=300)
        return JsonResponse(
            {"error": "Lokasi tidak ditemukan."},
            status=404,
        )

    try:
        latitude = Decimal(str(results[0]["lat"])).quantize(
            Decimal("0.000001"),
            rounding=ROUND_HALF_UP,
        )
        longitude = Decimal(str(results[0]["lon"])).quantize(
            Decimal("0.000001"),
            rounding=ROUND_HALF_UP,
        )

        result = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "display_name": results[0]["display_name"],
        }
    except (KeyError, TypeError, ValueError, IndexError, InvalidOperation):
        return JsonResponse(
            {"error": "Respons lokasi dari layanan tidak valid."},
            status=502,
        )

    if not (-90 <= result["latitude"] <= 90):
        return JsonResponse(
            {"error": "Koordinat latitude dari layanan tidak valid."},
            status=502,
        )

    if not (-180 <= result["longitude"] <= 180):
        return JsonResponse(
            {"error": "Koordinat longitude dari layanan tidak valid."},
            status=502,
        )

    cache.set(cache_key, result, timeout=86400)
    return JsonResponse(result)

@login_required
def create_listing(request):
    if request.method == "POST":
        form = FoodListingForm(request.POST)

        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.save()

            message = f"{listing.food_name} berhasil dibagikan di Dead Drop."

            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "dead_drop/partials/listing_form_result.html",
                    {
                        "listing": listing,
                        "message": message,
                        "success": True,
                    },
                )

            messages.success(request, message)
            return redirect("dead_drop:listing_board")
    else:
        form = FoodListingForm()

    context = {
        "form": form,
        "form_action": reverse("dead_drop:create_listing"),
        "form_title": "Bagikan Makanan",
        "submit_label": "Publikasikan",
    }

    if request.method == "POST" and request.headers.get("HX-Request") == "true":
        return render(
            request,
            "dead_drop/partials/listing_form_fragment.html",
            context,
        )

    return render(request, "dead_drop/food_listing_form.html", context)

@login_required
@require_POST
def reserve_listing(request, listing_id):
    listing = get_object_or_404(FoodListing, pk=listing_id)

    updated_count = (
        FoodListing.objects
        .filter(
            pk=listing_id,
            status=ListingStatus.AVAILABLE,
        )
        .exclude(owner=request.user)
        .update(
            status=ListingStatus.RESERVED,
            reserved_by=request.user,
            updated_at=timezone.now(),
        )
    )

    success = bool(updated_count)

    if success:
        message = f"Reservasi untuk {listing.food_name} berhasil dibuat."
        listing.refresh_from_db()
    else:
        message = "Makanan ini tidak dapat direservasi."

    if request.headers.get("HX-Request") == "true":
        return render_htmx_board(request, message, success)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("dead_drop:listing_board")

@login_required
@require_POST
def cancel_reserve_listing(request, listing_id):
    listing = get_object_or_404(FoodListing, pk=listing_id)

    updated_count = (
        FoodListing.objects
        .filter(
            pk=listing_id,
            status=ListingStatus.RESERVED,
        )
        .filter(
            Q(owner=request.user) | Q(reserved_by=request.user)
        )
        .update(
            status=ListingStatus.AVAILABLE,
            reserved_by=None,
            updated_at=timezone.now(),
        )
    )

    success = bool(updated_count)

    if success:
        message = f"Reservasi untuk {listing.food_name} berhasil dibatalkan."
        listing.refresh_from_db()
    else:
        message = "Reservasi ini tidak dapat dibatalkan."

    if request.headers.get("HX-Request") == "true":
        return render_htmx_board(request, message, success)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("dead_drop:listing_board")

@login_required
@require_POST
def claim_listing(request, listing_id):
    listing = get_object_or_404(FoodListing, pk=listing_id)
    now = timezone.now()
    updated_count = (
        FoodListing.objects
        .filter(
            pk=listing_id,
            owner=request.user,
            status=ListingStatus.RESERVED
        )
        .update(
            status=ListingStatus.CLAIMED,
            updated_at=now,
            claimed_at=now
        )
    )

    success = bool(updated_count)

    if success:
        message = f"{listing.food_name} berhasil ditandai sebagai sudah diklaim."
        listing.refresh_from_db()
    else:
        message = "Listing ini tidak dapat diklaim."

    if request.headers.get("HX-Request") == "true":
        return render_htmx_board(request, message, success)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("dead_drop:listing_board")

@login_required
def edit_listing(request, listing_id):
    listing = get_object_or_404(FoodListing, pk=listing_id)
    is_htmx = request.headers.get("HX-Request") == "true"

    if listing.owner != request.user or listing.status == ListingStatus.CLAIMED:
        message = "Listing ini tidak dapat diedit."

        if is_htmx:
            return render(
                request,
                "dead_drop/partials/listing_form_result.html",
                {"message": message, "success": False},
            )

        messages.error(request, message)
        return redirect("dead_drop:listing_board")

    if request.method == "POST":
        form = FoodListingForm(request.POST, instance=listing)

        if form.is_valid():
            listing = form.save()
            message = f"{listing.food_name} berhasil diperbarui."

            if is_htmx:
                return render(
                    request,
                    "dead_drop/partials/listing_form_result.html",
                    {
                        "listing": listing,
                        "message": message,
                        "success": True,
                    },
                )

            messages.success(request, message)
            return redirect("dead_drop:listing_board")
    else:
        form = FoodListingForm(instance=listing)

    context = {
        "form": form,
        "form_action": reverse(
            "dead_drop:edit_listing",
            kwargs={"listing_id": listing.pk},
        ),
        "form_title": "Edit listing",
        "submit_label": "Simpan perubahan",
    }

    if request.method == "POST" and is_htmx:
        return render(
            request,
            "dead_drop/partials/listing_form_fragment.html",
            context,
        )

    return render(request, "dead_drop/food_listing_form.html", context)

@login_required
@require_POST
def delete_listing(request, listing_id):
    listing = get_object_or_404(FoodListing, pk=listing_id)

    deleted_count, _ = FoodListing.objects.filter(
        pk=listing_id,
        owner=request.user,
        status=ListingStatus.AVAILABLE
    ).delete()

    if request.headers.get("HX-Request") == "true":
        if deleted_count:
            return render_htmx_board(
                request,
                f"{listing.food_name} berhasil dihapus.",
                True,
            )
        return render_htmx_board(
            request,
            "Listing ini tidak dapat dihapus.",
            False,
        )

    if deleted_count:
        messages.success(request, f"{listing.food_name} berhasil dihapus.")
    else:
        messages.error(request, "Listing ini tidak dapat dihapus.")

    return redirect("dead_drop:listing_board")
