"""Endpoint DRF modul Recipe Alchemist (prefiks /api/recipes/). Diisi oleh: Nuno.

Checkpoint 1 (wajib sudah jalan, sebaiknya juga di PWS):
    GET  /api/recipes/                        -> recipe_list: Daftar resep ?scope=mine|community&q=&diet=
    GET  /api/recipes/<id>/                   -> recipe_detail: Detail resep; notes hanya untuk pemilik

Final submission:
    POST, PUT/PATCH, DELETE resep (hanya pemilik)
    GET search/?ingredients=&max_minutes=&diet= (Spoonacular)
    POST save-api/

Aturan bersama (lihat docs/API_MOBILE.md):
- Pakai pola fungsi @api_view seperti Tutorial 07; route didaftarkan di api_urls.py modul ini.
- Default proyek: SessionAuthentication + IsAuthenticated (REST_FRAMEWORK di settings.py).
- Akses data: scope=community boleh dibaca tamu (resep is_public=True); scope=mine wajib login.
    Tulis @permission_classes([AllowAny]) lalu tolak sendiri scope=mine untuk tamu,
    atau pisahkan endpoint. Field notes hanya untuk pemilik (lihat Recipe.to_dict(include_private)).
- Jangan pakai @csrf_exempt. Request tulis dari Flutter membawa token CSRF (docs/API_MOBILE.md).
- Error memakai format bawaan DRF: {"detail": "..."} atau {"nama_field": ["pesan"]}.
"""
from django.shortcuts import get_object_or_404  # noqa: F401
from rest_framework import status  # noqa: F401
from rest_framework.decorators import api_view, permission_classes  # noqa: F401
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly  # noqa: F401
from rest_framework.response import Response  # noqa: F401

from recipe_alchemist.models import Recipe  # noqa: F401

# TODO (Checkpoint 1): recipe_list, recipe_detail
