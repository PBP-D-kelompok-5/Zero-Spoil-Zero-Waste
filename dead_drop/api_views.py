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
from django.shortcuts import get_object_or_404  # noqa: F401
from rest_framework import status  # noqa: F401
from rest_framework.decorators import api_view, permission_classes  # noqa: F401
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly  # noqa: F401
from rest_framework.response import Response  # noqa: F401

from dead_drop.models import FoodListing  # noqa: F401

# TODO (Checkpoint 1): listing_list, listing_detail
