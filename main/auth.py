"""Alur autentikasi bersama untuk semua modul (mengikuti pola Pantry Death Clock).

Aturan yang dipakai di seluruh aplikasi:
1. Halaman/aksi yang butuh login memakai ``login_required_ajax``:
   * permintaan biasa  -> redirect ke halaman masuk dengan ``?next=`` ke halaman asal;
   * AJAX / JSON       -> 401 JSON ``{"ok": false, "detail": ..., "login_url": ...}``;
   * HTMX              -> header ``HX-Redirect`` ke halaman masuk (seluruh halaman pindah,
                          bukan halaman login yang tertempel di dalam potongan HTML).
2. Halaman daftar yang datanya privat memakai ``guest_page``: tamu melihat halaman
   pengenalan modul (dengan tombol Masuk/Daftar), bukan dilempar ke halaman masuk.
3. Objek milik pengguna lain dianggap tidak ada (404), agar keberadaannya tidak bocor.
4. Tujuan ``next`` dari input pengguna hanya boleh mengarah ke situs ini sendiri.
5. Endpoint sensitif dibatasi jumlah permintaannya (``rate_limit``; percobaan login gagal
   lewat ``LoginThrottle``). Melebihi batas -> 429 (``rate_limit`` juga mengirim ``Retry-After``).
"""
import math
import time
from functools import wraps
from urllib.parse import urlsplit

from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
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


def is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def htmx_login_redirect(request):
    """Tamu yang memicu aksi HTMX diarahkan ke halaman masuk, lalu kembali ke halaman yang sedang dibuka."""
    current = request.headers.get('HX-Current-URL', '')
    parts = urlsplit(current)
    next_path = parts.path + (f'?{parts.query}' if parts.query else '')
    if not next_path or not url_has_allowed_host_and_scheme(
        current, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_path = request.get_full_path()
    response = HttpResponse(status=204)
    response['HX-Redirect'] = redirect_to_login(next_path).url
    return response


def login_required_ajax(view):
    """Seperti ``@login_required``, tetapi AJAX/JSON mendapat 401 JSON dan HTMX mendapat HX-Redirect."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        if is_htmx(request):
            return htmx_login_redirect(request)
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


# ---------- Rate limiting ----------
# Penghitung disimpan di cache Django (bawaan: LocMemCache, per proses server). Cukup untuk
# menahan klik/skrip beruntun; untuk beberapa worker sekaligus pakai cache bersama (mis. Redis).
RATE_LIMIT_MESSAGE = 'Terlalu banyak permintaan. Coba lagi dalam {seconds} detik.'


def client_ip(request):
    return request.META.get('REMOTE_ADDR') or 'unknown'


def _hit(cache_key, window):
    """Tambah penghitung di jendela waktu tetap; kembalikan jumlah setelah ditambah."""
    cache.add(cache_key, 0, window)
    try:
        return cache.incr(cache_key)
    except ValueError:  # kunci kedaluwarsa tepat di antara add() dan incr()
        cache.set(cache_key, 1, window)
        return 1


def _retry_after(window):
    return max(1, math.ceil(window - time.time() % window))


def too_many_requests(request, retry_after, detail=None):
    detail = detail or RATE_LIMIT_MESSAGE.format(seconds=retry_after)
    if wants_json(request):
        response = JsonResponse({'ok': False, 'detail': detail, 'retry_after': retry_after}, status=429)
    else:
        response = render(request, '429.html', {'detail': detail}, status=429)
    response['Retry-After'] = str(retry_after)
    return response


def rate_limit(scope, limit, window=60, methods=('POST',)):
    """Batasi ``limit`` permintaan per ``window`` detik untuk tiap pengguna (tamu: per IP).

    ``scope`` memisahkan penghitung antar-endpoint, mis. ``rate_limit('death_clock:bulk', 10)``.
    Hanya metode di ``methods`` yang dihitung (bawaan: POST, yaitu aksi yang mengubah data).
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method in methods:
                who = f'u{request.user.pk}' if request.user.is_authenticated else f'ip{client_ip(request)}'
                bucket = int(time.time() // window)
                if _hit(f'rl:{scope}:{who}:{bucket}', window) > limit:
                    return too_many_requests(request, _retry_after(window))
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


class LoginThrottle:
    """Batas percobaan login GAGAL per pasangan (IP, username): menahan tebak-tebakan password.

    Login yang berhasil menghapus penghitungnya. Saat terkunci, password tidak diperiksa sama sekali.
    """

    limit = 5
    window = 5 * 60

    def __init__(self, request, username):
        self.key = f'rl:login:{client_ip(request)}:{(username or "").strip().casefold()}'

    def blocked_for(self):
        """Detik tersisa sampai boleh mencoba lagi, atau 0 bila belum terkunci."""
        if cache.get(self.key, 0) < self.limit:
            return 0
        expires_at = cache.get(f'{self.key}:until')
        return max(1, math.ceil(expires_at - time.time())) if expires_at else self.window

    def failed(self):
        if cache.add(f'{self.key}:until', time.time() + self.window, self.window):
            cache.set(self.key, 0, self.window)
        _hit(self.key, self.window)

    def reset(self):
        cache.delete_many([self.key, f'{self.key}:until'])
