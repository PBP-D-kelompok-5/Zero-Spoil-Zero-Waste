from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect

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
