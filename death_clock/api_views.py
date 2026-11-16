"""Endpoint DRF modul Pantry Death Clock (prefiks /api/death-clock/). Diisi oleh: Michael Evan.

Checkpoint 1 (wajib sudah jalan, sebaiknya juga di PWS):
    GET  /api/death-clock/items/              -> item_list: Daftar bahan milik pengguna (filter status, category, storage, q)
    GET  /api/death-clock/items/<id>/         -> item_detail: Detail satu bahan

Final submission:
    POST items/  (expiry_date kosong -> estimate_expiry())
    PUT/PATCH/DELETE items/<id>/
    POST items/<id>/resurrect/ dan items/<id>/revive/
    GET summary/

Aturan bersama (lihat docs/API_MOBILE.md):
- Pakai pola fungsi @api_view seperti Tutorial 07; route didaftarkan di api_urls.py modul ini.
- Default proyek: SessionAuthentication + IsAuthenticated (REST_FRAMEWORK di settings.py).
- Akses data: Data privat per pengguna: GET pun wajib login (default IsAuthenticated sudah sesuai).
    Ambil data lewat PantryItem.objects.filter(user=request.user); item milik orang lain -> 404.
- Jangan pakai @csrf_exempt. Request tulis dari Flutter membawa token CSRF (docs/API_MOBILE.md).
- Error memakai format bawaan DRF: {"detail": "..."} atau {"nama_field": ["pesan"]}.
"""
from django.shortcuts import get_object_or_404  # noqa: F401
from rest_framework import status  # noqa: F401
from rest_framework.decorators import api_view, permission_classes  # noqa: F401
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly  # noqa: F401
from rest_framework.response import Response  # noqa: F401

from death_clock.models import PantryItem  # noqa: F401

# TODO (Checkpoint 1): item_list, item_detail
