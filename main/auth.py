"""Alur autentikasi bersama untuk semua modul (mengikuti pola Pantry Death Clock).

Aturan yang dipakai di seluruh aplikasi:
1. Halaman/aksi yang butuh login memakai ``login_required_ajax``:
   * permintaan biasa  -> redirect ke halaman masuk dengan ``?next=`` ke halaman asal;
   * AJAX / JSON       -> 401 JSON ``{"ok": false, "detail": ..., "login_url": ...}``.
2. Halaman daftar yang datanya privat memakai ``guest_page``: tamu melihat halaman
   pengenalan modul (dengan tombol Masuk/Daftar), bukan dilempar ke halaman masuk.
3. Objek milik pengguna lain dianggap tidak ada (404), agar keberadaannya tidak bocor.
4. Tujuan ``next`` dari input pengguna hanya boleh mengarah ke situs ini sendiri.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

LOGIN_MESSAGE = 'Silakan masuk terlebih dahulu.'


def is_ajax(request):
    """Permintaan dari JavaScript (fetch/XHR) atau yang meminta format JSON."""
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.GET.get('format') == 'json'
    )


def wants_json(request):
    """AJAX, atau endpoint web service (``.../json/...``) yang selalu menjawab JSON."""
    return is_ajax(request) or '/json/' in request.path


def unauthorized_json(detail=LOGIN_MESSAGE):
    return JsonResponse({'ok': False, 'detail': detail, 'login_url': reverse('main:login')}, status=401)


def login_required_ajax(view):
    """Seperti ``@login_required``, tetapi AJAX/JSON mendapat 401 JSON, bukan redirect."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        if wants_json(request):
            return unauthorized_json()
        return redirect_to_login(request.get_full_path())

    return wrapper


def guest_page(template_name, context=None):
    """Untuk halaman daftar privat: tamu melihat ``template_name`` (pengenalan modul + ajakan masuk)."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view(request, *args, **kwargs)
            if wants_json(request):
                return unauthorized_json()
            return render(request, template_name, context or {})

        return wrapper

    return decorator


def safe_next_url(request, fallback):
    """Ambil ``next`` (POST/GET) hanya jika mengarah ke situs ini; selain itu pakai ``fallback``."""
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return fallback
