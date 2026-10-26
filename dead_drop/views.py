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

            messages.success(
                request,
                f"{listing.food_name} berhasil dibagikan di Dead Drop.",
            )
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

    if updated_count:
        messages.success(
            request,
            f"Reservasi untuk {listing.food_name} berhasil dibuat.",
        )
    else:
        messages.error(request, "Makanan ini tidak dapat direservasi.")

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

    if updated_count:
        messages.success(
            request,
            f"Reservasi untuk {listing.food_name} berhasil dibatalkan.",
        )
    else:
        messages.error(request, "Reservasi ini tidak dapat dibatalkan.")

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

    if updated_count:
        messages.success(
            request,
            f"{listing.food_name} berhasil ditandai sebagai sudah diklaim.",
        )
    else:
        messages.error(request, "Listing ini tidak dapat diklaim.")

    return redirect("dead_drop:listing_board")

@login_required
def edit_listing(request, listing_id):
    listing = get_object_or_404(FoodListing, pk=listing_id)

    if listing.owner != request.user or listing.status == ListingStatus.CLAIMED:
        messages.error(request, "Listing ini tidak dapat diedit.")
        return redirect("dead_drop:listing_board")

    if request.method == "POST":
        form = FoodListingForm(request.POST, instance=listing)

        if form.is_valid():
            form.save()
            messages.success(request, f"{listing.food_name} berhasil diperbarui.")
            return redirect("dead_drop:listing_board")
    else:
        form = FoodListingForm(instance=listing)

    context = {
        "form": form
    }

    return render(request,"dead_drop/food_listing_form.html",context)

@login_required
@require_POST
def delete_listing(request, listing_id):
    listing = get_object_or_404(FoodListing, pk=listing_id)

    deleted_count, _ = FoodListing.objects.filter(
        pk=listing_id,
        owner=request.user,
        status=ListingStatus.AVAILABLE
    ).delete()

    if deleted_count:
        messages.success(request, f"{listing.food_name} berhasil dihapus.")
    else:
        messages.error(request, "Listing ini tidak dapat dihapus.")

    return redirect("dead_drop:listing_board")
