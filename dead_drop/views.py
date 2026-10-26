from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

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

def listing_board(request):
    queryset = visible_listing_for(request.user).select_related("owner", "reserved_by")

    context = {
        "available_listings": queryset.filter(status=ListingStatus.AVAILABLE),
        "reserved_listings": queryset.filter(status=ListingStatus.RESERVED),
        "claimed_listings": queryset.filter(status=ListingStatus.CLAIMED),
    }

    return render(request, "dead_drop/listing_board.html", context)

@login_required
def create_listing(request):
    if request.method == "POST":
        form = FoodListingForm(request.POST)

        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.save()

            messages.success(request, f"{listing.food_name} berhasil dibagikan di Dead Drop")
            return redirect("dead_drop:listing_board")

    else:
        form = FoodListingForm()

    context = {
        "form": form
    }

    return render(request, "dead_drop/food_listing_form.html", context)

@login_required
@require_POST
def reserve_listing(request, listing_id):
    listing = get_object_or_404(FoodListing, pk=listing_id)

    updated = (
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

    if updated:
        messages.success(request, f"{listing.food_name} berhasil kamu reservasi.")
    else:
        messages.error(request, "Makanan ini tidak tersedia untuk direservasi")

    return redirect("dead_drop:listing_board")

@login_required
@require_POST
def cancel_reserve_listing(request, listing_id):
    listing = get_object_or_404(FoodListing, pk=listing_id)

    updated = (
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

    if updated:
        messages.success(request, f"Reservasi {listing.food_name} berhasil kamu batalkan.")
    else:
        messages.error(request, "Reservasi makanan ini tidak bisa dibatalkan")

    return redirect("dead_drop:listing_board")

@login_required
@require_POST
def claim_listing(request, listing_id):
    listing = get_object_or_404(FoodListing, pk=listing_id)
    updated = (
        FoodListing.objects
        .filter(
            pk=listing_id,
            status=ListingStatus.RESERVED
        )
        .filter(
            Q(owner=request.user)
        )
        .update(
            status=ListingStatus.CLAIMED,
            updated_at=timezone.now(),
            claimed_at=timezone.now()
        )
    )

    if updated:
        messages.success(request, f"Reservasi {listing.food_name} berhasil kamu claim.")
    else:
        messages.error(request, "Reservasi makanan ini tidak bisa di claim")

    return redirect("dead_drop:listing_board")
    