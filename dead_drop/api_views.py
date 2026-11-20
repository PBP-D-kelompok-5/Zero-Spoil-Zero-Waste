"""Endpoint DRF modul The Dead Drop (prefiks /api/dead-drop/). Diisi oleh: Joshua.

Checkpoint 1 (wajib sudah jalan, sebaiknya juga di PWS):
    GET  /api/dead-drop/listings/             -> listing_list: Daftar listing ?status=
    GET  /api/dead-drop/listings/<id>/        -> listing_detail: Detail listing

Final submission:
    POST, PUT/PATCH, DELETE listings/ (hanya owner)
    POST listings/<id>/reserve/, cancel/, claim/ (aturan transisi sama dengan views.py)
    GET geocode/?q= (OpenStreetMap)

Aturan bersama (lihat docs/API_MOBILE.md):
- Pakai pola fungsi @api_view seperti Tutorial 07; route didaftarkan di api_urls.py modul ini.
- Default proyek: SessionAuthentication + IsAuthenticated (REST_FRAMEWORK di settings.py).
- Akses data: Listing boleh dibaca tamu: tulis @permission_classes([IsAuthenticatedOrReadOnly])
    (atau AllowAny untuk view yang hanya GET). Ubah/hapus hanya oleh owner.
- Jangan pakai @csrf_exempt. Request tulis dari Flutter membawa token CSRF (docs/API_MOBILE.md).
- Error memakai format bawaan DRF: {"detail": "..."} atau {"nama_field": ["pesan"]}.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dead_drop.models import FoodListing, ListingStatus
from dead_drop.serializers import FoodListingSerializer


def visible_listings_for(user):
    """Match the web board's visibility: available is public; other states are private."""
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


@api_view(["GET"])
@permission_classes([AllowAny])
def listing_list(request):
    queryset = visible_listings_for(request.user).select_related("owner", "reserved_by")
    requested_status = request.query_params.get("status", "").strip().lower()

    if requested_status:
        if requested_status not in ListingStatus.values:
            return Response(
                {"detail": "Status listing tidak dikenal."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = queryset.filter(status=requested_status)

    serializer = FoodListingSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def listing_detail(request, pk):
    listing = get_object_or_404(
        visible_listings_for(request.user).select_related("owner", "reserved_by"),
        pk=pk,
    )
    serializer = FoodListingSerializer(listing)
    return Response(serializer.data)
