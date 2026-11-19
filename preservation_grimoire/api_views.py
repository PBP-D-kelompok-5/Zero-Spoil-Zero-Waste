"""Endpoint DRF modul Preservation Grimoire & Smell Test (prefiks /api/grimoire/). Diisi oleh: Syarif.

Checkpoint 1 (wajib sudah jalan, sebaiknya juga di PWS):
    GET  /api/grimoire/guides/                -> guide_list: Daftar panduan ?category=&method=&q=
    GET  /api/grimoire/guides/<id>/           -> guide_detail: Detail panduan

Final submission:
    POST, PUT/PATCH, DELETE guides/ (hanya author)
    POST guides/<id>/upvote/ (toggle)

Aturan bersama (lihat docs/API_MOBILE.md):
- Pakai pola fungsi @api_view seperti Tutorial 07; route didaftarkan di api_urls.py modul ini.
- Default proyek: SessionAuthentication + IsAuthenticated (REST_FRAMEWORK di settings.py).
- Akses data: Panduan boleh dibaca tamu: tulis @permission_classes([IsAuthenticatedOrReadOnly])
    (atau AllowAny untuk view yang hanya GET). Ubah/hapus hanya oleh author.
- Jangan pakai @csrf_exempt. Request tulis dari Flutter membawa token CSRF (docs/API_MOBILE.md).
- Error memakai format bawaan DRF: {"detail": "..."} atau {"nama_field": ["pesan"]}.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status  # noqa: F401
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly  # noqa: F401
from rest_framework.response import Response

from preservation_grimoire.models import PreservationGuide
from preservation_grimoire.serializers import PreservationGuideSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def guide_list(request):
    queryset = (
        PreservationGuide.objects.select_related('author')
        .prefetch_related('upvotes')
        .all()
        .order_by('-created_at')
    )

    category = request.query_params.get('category', '').strip().upper()
    if category:
        queryset = queryset.filter(category=category)

    method = request.query_params.get('method', '').strip()
    if method:
        queryset = queryset.filter(preservation_method__icontains=method)

    q = request.query_params.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(preservation_method__icontains=q)
            | Q(content__icontains=q)
        )

    serializer = PreservationGuideSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def guide_detail(request, pk):
    guide = get_object_or_404(
        PreservationGuide.objects.select_related('author').prefetch_related('upvotes'),
        pk=pk,
    )
    serializer = PreservationGuideSerializer(guide)
    return Response(serializer.data)