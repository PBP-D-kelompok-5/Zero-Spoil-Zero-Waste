"""Endpoint DRF modul Pantry Death Clock (prefiks /api/death-clock/). Diisi oleh: Michael Evan.

Checkpoint 1:
    GET  /api/death-clock/items/        -> item_list: bahan milik pengguna, filter ?status=&category=&storage=&q=
    GET  /api/death-clock/items/<id>/   -> item_detail: detail satu bahan

Final submission:
    POST items/  (expiry_date kosong -> estimate_expiry())
    PUT/PATCH/DELETE items/<id>/
    POST items/<id>/resurrect/ dan items/<id>/revive/
    GET summary/

Aturan akses: data privat per pengguna. Semua endpoint wajib login (403 untuk tamu), dan bahan
milik pengguna lain dibalas 404 supaya keberadaannya tidak bocor, sama seperti situs web.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from death_clock.forms import FilterForm
from death_clock.models import PantryItem
from death_clock.serializers import PantryItemSerializer
from death_clock.views import filter_items


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def item_list(request):
    """Daftar bahan. Tanpa ?status= hanya bahan aktif (belum diolah), sama dengan situs web.

    status: FLATLINING | CRITICAL | STABLE | RESURRECTED
    category: VEG | MEAT | DAIRY | GRAIN | OTHER
    storage: FRIDGE | FREEZER | PANTRY
    q: cari di nama bahan atau catatan
    """
    filter_form = FilterForm(request.query_params)
    if not filter_form.is_valid():
        errors = {
            field: [str(message) for message in messages]
            for field, messages in filter_form.errors.items()
        }
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    items = filter_items(PantryItem.objects.filter(user=request.user), filter_form.values)
    return Response(PantryItemSerializer(items, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def item_detail(request, pk):
    item = get_object_or_404(PantryItem, pk=pk, user=request.user)
    return Response(PantryItemSerializer(item).data)
