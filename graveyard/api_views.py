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
from django.shortcuts import get_object_or_404  # noqa: F401
from rest_framework import status  # noqa: F401
from rest_framework.decorators import api_view, permission_classes  # noqa: F401
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly  # noqa: F401
from rest_framework.response import Response  # noqa: F401

from graveyard.models import GraveyardItem  # noqa: F401

# TODO (Checkpoint 1): item_list, item_detail
