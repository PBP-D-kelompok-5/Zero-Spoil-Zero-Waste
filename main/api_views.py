"""Endpoint autentikasi JSON (DRF) untuk aplikasi Flutter, prefiks ``/api/auth/``.

Login memakai session Django yang sama dengan situs web, jadi data yang diubah dari aplikasi
langsung terlihat di situs PWS. Bentuk respons ``{"status": bool, "message": str, ...}``
mengikuti konvensi ``CookieRequest`` dari paket ``pbp_django_auth``.

    POST /api/auth/login/      username, password             -> 200 | 400 | 401 | 429
    POST /api/auth/register/   username, password1, password2 -> 201 | 400 | 429
    POST /api/auth/logout/                                    -> 200
    GET  /api/auth/me/         status login saat ini          -> 200
    GET  /api/auth/csrf/       token CSRF untuk request tulis -> 200

Input boleh JSON (``postJson``) maupun form-encoded (``CookieRequest.login``).

Kenapa login, register, dan logout tidak memeriksa CSRF: klien belum punya token sebelum
login, sama seperti pola ``@csrf_exempt`` pada login Flutter di PBP. Ketiganya ditulis dengan
``@authentication_classes([])`` sehingga DRF tidak menjalankan SessionAuthentication (yang
memeriksa CSRF). Semua endpoint modul yang MENGUBAH data tetap wajib membawa token CSRF;
lihat ``docs/API_MOBILE.md``.
"""
import math

from django.contrib.auth import authenticate, get_user, login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes, throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from main.auth import LoginThrottle
from main.forms import RegisterForm


class RegisterThrottle(AnonRateThrottle):
    """Batasi pembuatan akun dari satu IP (menahan skrip pendaftaran massal)."""

    scope = 'auth_register'
    rate = '10/hour'


def _payload(request):
    """``request.data`` sebagai dict; body JSON yang bukan objek dianggap kosong."""
    return request.data if hasattr(request.data, 'get') else {}


def _field(data, name):
    value = data.get(name, '')
    return value if isinstance(value, str) else ''


def _user_json(user):
    return {'id': user.pk, 'username': user.username}


def _form_errors(form):
    return {field: [str(message) for message in messages] for field, messages in form.errors.items()}


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login_api(request):
    data = _payload(request)
    username = _field(data, 'username').strip()
    password = _field(data, 'password')
    if not username or not password:
        return Response(
            {'status': False, 'message': 'Username dan password wajib diisi.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Batas percobaan gagal yang sama dengan halaman login web (main.auth.LoginThrottle).
    throttle = LoginThrottle(request, username)
    wait = throttle.blocked_for()
    if wait:
        response = Response(
            {
                'status': False,
                'message': f'Terlalu banyak percobaan masuk yang gagal. Coba lagi dalam {math.ceil(wait / 60)} menit.',
                'retry_after': wait,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        response['Retry-After'] = str(wait)
        return response

    user = authenticate(request, username=username, password=password)
    if user is None:  # ModelBackend juga menolak akun yang dinonaktifkan
        throttle.failed()
        return Response(
            {'status': False, 'message': 'Username atau password salah.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    throttle.reset()
    login(request, user)
    return Response({
        'status': True,
        'message': f'Selamat datang kembali, {user.username}!',
        'username': user.username,
        'user': _user_json(user),
        # login() merotasi token CSRF; token baru ini juga dikirim sebagai cookie csrftoken.
        'csrf_token': get_token(request),
    })


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([RegisterThrottle])
def register_api(request):
    data = _payload(request)
    form = RegisterForm(data={
        'username': _field(data, 'username'),
        'password1': _field(data, 'password1'),
        'password2': _field(data, 'password2'),
    })
    if not form.is_valid():
        errors = _form_errors(form)
        first_error = next(iter(errors.values()))[0]
        return Response(
            {'status': False, 'message': first_error, 'errors': errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Sengaja tidak langsung login: aplikasi diarahkan ke halaman login setelah daftar,
    # supaya status login di CookieRequest selalu berasal dari /api/auth/login/.
    user = form.save()
    return Response(
        {
            'status': True,
            'message': f'Akun {user.username} berhasil dibuat. Silakan masuk.',
            'username': user.username,
            'user': _user_json(user),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def logout_api(request):
    # Tanpa authentication class, DRF mengisi request.user dengan AnonymousUser,
    # jadi user yang sedang login dibaca langsung dari session.
    django_request = request._request
    user = get_user(django_request)
    username = user.username if user.is_authenticated else ''
    logout(django_request)
    return Response({
        'status': True,
        'message': 'Kamu sudah keluar. Sampai jumpa lagi!',
        'username': username,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def me_api(request):
    """Cek apakah session di aplikasi masih login (dipakai saat aplikasi dibuka)."""
    if request.user.is_authenticated:
        return Response({'status': True, 'is_authenticated': True, 'user': _user_json(request.user)})
    return Response({'status': True, 'is_authenticated': False, 'user': None})


@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_api(request):
    """Ambil token CSRF (juga dipasang sebagai cookie ``csrftoken``) sebelum request tulis."""
    return Response({'status': True, 'csrf_token': get_token(request)})
