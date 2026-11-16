"""Endpoint DRF modul The Graveyard & Waste Analytics (prefiks /api/graveyard/). Diisi oleh: Adam.

Checkpoint 1 (wajib sudah jalan, sebaiknya juga di PWS):
    GET  /api/graveyard/items/                -> item_list: Riwayat ?category=&reason=&q=&date_from=&date_to=
    GET  /api/graveyard/items/<id>/           -> item_detail: Detail satu catatan

Final submission:
    POST, PUT/PATCH, DELETE items/
    GET analytics/ (calculate_analytics())
    POST move/<pantry_item_id>/ (koordinasi dengan Death Clock)

Aturan bersama (lihat docs/API_MOBILE.md):
- Pakai pola fungsi @api_view seperti Tutorial 07; route didaftarkan di api_urls.py modul ini.
- Default proyek: SessionAuthentication + IsAuthenticated (REST_FRAMEWORK di settings.py).
- Akses data: Data privat per pengguna: GET pun wajib login (default IsAuthenticated sudah sesuai).
    Ambil data lewat GraveyardItem.objects.filter(user=request.user); milik orang lain -> 404.
- Jangan pakai @csrf_exempt. Request tulis dari Flutter membawa token CSRF (docs/API_MOBILE.md).
- Error memakai format bawaan DRF: {"detail": "..."} atau {"nama_field": ["pesan"]}.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from graveyard.models import GraveyardItem
from graveyard.serializers import GraveyardItemSerializer
from graveyard.views import parse_date_param


@api_view(['GET', 'POST'])
def item_list(request):
    """Mengambil daftar catatan Graveyard milik pengguna (beserta filter) atau membuat baru."""
    if request.method == 'GET':
        user_items = GraveyardItem.objects.filter(user=request.user)

        category_filter = request.query_params.get('category', '').strip()
        reason_filter = request.query_params.get('reason', '').strip()
        query = request.query_params.get('q', '').strip()

        if category_filter:
            user_items = user_items.filter(category=category_filter)
        if reason_filter:
            user_items = user_items.filter(reason=reason_filter)
        if query:
            user_items = user_items.filter(
                Q(name__icontains=query) | Q(notes__icontains=query)
            )

        date_from = parse_date_param(request.query_params.get('date_from'))
        date_to = parse_date_param(request.query_params.get('date_to'))
        if date_from and date_to and date_from > date_to:
            date_from, date_to = date_to, date_from
        if date_from:
            user_items = user_items.filter(disposed_at__gte=date_from)
        if date_to:
            user_items = user_items.filter(disposed_at__lte=date_to)

        serializer = GraveyardItemSerializer(user_items, many=True)
        return Response(serializer.data)

    serializer = GraveyardItemSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def item_detail(request, pk):
    """Membaca, memperbarui, atau menghapus satu catatan Graveyard milik pengguna."""
    item = get_object_or_404(GraveyardItem, pk=pk, user=request.user)

    if request.method == 'GET':
        serializer = GraveyardItemSerializer(item)
        return Response(serializer.data)

    if request.method in ('PUT', 'PATCH'):
        serializer = GraveyardItemSerializer(
            item,
            data=request.data,
            partial=(request.method == 'PATCH'),
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
