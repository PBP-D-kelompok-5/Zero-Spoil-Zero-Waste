from django.db.models import Q
from django.shortcuts import render

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