# Web Service DRF untuk Aplikasi Mobile

Panduan bersama untuk endpoint Django REST Framework (DRF) yang dipakai aplikasi Flutter
Pantry Necromancer. Endpoint `/json/` lama tetap dipakai situs web dan tidak diubah.

## Yang sudah disiapkan

| Bagian | Lokasi |
|---|---|
| DRF dan django-cors-headers | `requirements.txt`, `INSTALLED_APPS`, `MIDDLEWARE` |
| Default DRF: `SessionAuthentication` + `IsAuthenticated` | `REST_FRAMEWORK` di `settings.py` |
| Host emulator Android `10.0.2.2` | `ALLOWED_HOSTS` |
| CORS dan CSRF untuk Flutter web di port 5000 | `FLUTTER_WEB_ORIGINS` di `settings.py` |
| Endpoint auth JSON | `main/api_views.py`, `main/api_urls.py` |
| File kerangka API setiap modul | `<app>/serializers.py`, `<app>/api_views.py`, `<app>/api_urls.py` |
| Route `/api/<modul>/` | `PantryNecromancer/urls.py` |

## Tugas setiap anggota untuk Checkpoint 1

Kerjakan hanya di file modulmu sendiri supaya tidak konflik:

1. `serializers.py`: buat `ModelSerializer`. Ikuti field di `to_dict()` model kamu.
2. `api_views.py`: buat view list dan detail dengan pola `@api_view` dari Tutorial 07.
3. `api_urls.py`: buka komentar route yang sudah disiapkan.
4. Cek di browser lewat Browsable API, misalnya `http://localhost:8000/api/grimoire/guides/`.
   Login dulu lewat `/login/` atau `/api-auth/login/`. Tambahkan `?format=json` untuk melihat JSON mentah.
5. Tulis tes di `tests.py` modulmu, lalu commit dari akun GitHub sendiri.

| Modul | Prefiks | Endpoint Checkpoint 1 | Akses baca |
|---|---|---|---|
| Death Clock (Evan) | `/api/death-clock/` | `items/`, `items/<id>/` | login, data sendiri |
| Recipe Alchemist (Nuno) | `/api/recipes/` | `?scope=mine\|community`, `<id>/` | community boleh tamu |
| Dead Drop (Joshua) | `/api/dead-drop/` | `listings/`, `listings/<id>/` | boleh tamu |
| Graveyard (Adam) | `/api/graveyard/` | `items/`, `items/<id>/` | login, data sendiri |
| Grimoire (Syarif) | `/api/grimoire/` | `guides/`, `guides/<id>/` | boleh tamu |

### Aturan akses

- Default proyek adalah `IsAuthenticated`. Endpoint yang boleh dibaca tamu wajib menulis
  `@permission_classes([IsAuthenticatedOrReadOnly])`, atau `AllowAny` untuk view yang hanya GET.
- Data privat: ambil lewat `Model.objects.filter(user=request.user)`, lalu `get_object_or_404`.
  Data milik orang lain dibalas 404, sama seperti situs web.
- Ubah dan hapus hanya oleh pemilik. Kalau bukan pemilik, balas 403 atau 404.
- Tamu yang memanggil endpoint wajib login mendapat **403** `{"detail": "..."}`. Ini perilaku
  `SessionAuthentication`, bukan 401.
- Jangan pakai `@csrf_exempt` di endpoint modul.

### Format respons

- Sukses: objek JSON untuk detail, list JSON untuk daftar (tanpa pagination).
- Error dari DRF: `{"detail": "pesan"}`, atau error per field `{"nama_field": ["pesan"]}` dengan status 400.
  Flutter cukup menampilkan pesan di field yang namanya sama.
- Tanggal memakai format ISO (`2026-11-20`), sama dengan `to_dict()`.

## Endpoint auth (`/api/auth/`)

| Method | Path | Body | Respons sukses |
|---|---|---|---|
| POST | `login/` | `username`, `password` | 200 `{status: true, message, username, user: {id, username}, csrf_token}` |
| POST | `register/` | `username`, `password1`, `password2` | 201 `{status: true, message, username, user}` |
| POST | `logout/` | (kosong) | 200 `{status: true, message, username}` |
| GET | `me/` | | 200 `{status: true, is_authenticated, user}` |
| GET | `csrf/` | | 200 `{status: true, csrf_token}` |

- Body boleh JSON atau form-encoded. `CookieRequest.login()` dari `pbp_django_auth` langsung cocok.
- Gagal login: 401 `{status: false, message}`. Kosong: 400. Lima kali gagal: 429 dengan `retry_after`
  (sama dengan halaman login web).
- Gagal daftar: 400 `{status: false, message, errors: {field: [pesan]}}`. Daftar tidak otomatis login;
  arahkan pengguna ke halaman login.

## Request tulis dari Flutter (POST/PUT/PATCH/DELETE)

DRF memeriksa CSRF untuk pengguna yang login lewat session (Tutorial 07). Setiap request tulis
ke endpoint modul harus membawa:

1. Cookie `sessionid` dan `csrftoken` dari respons login. `CookieRequest` menyimpannya otomatis.
2. Header `X-CSRFToken: <csrf_token>`. Ambil dari respons login, atau dari `GET /api/auth/csrf/`.
3. Header `Origin: <BASE_URL>`, misalnya `https://michael-evan51-pantry-necromancer.pws.cs.ui.ac.id`.
   Browser mengirimnya sendiri; klien HTTP di APK harus menambahkannya. Tanpa header ini,
   Django menolak request HTTPS dengan pesan "Referer checking failed".

Klien HTTP bersama di repo Flutter akan menambahkan header ini, jadi kode modul cukup memanggilnya.
Kalau request tulis mendapat 403, cek: sudah login, token CSRF terkirim, dan header `Origin` benar.

## Tes lokal

- Django: `python manage.py runserver 0.0.0.0:8000`.
- Emulator Android: base URL `http://10.0.2.2:8000`.
- HP fisik: pakai PWS. IP laptop di jaringan lokal tidak ada di `ALLOWED_HOSTS`.
- Flutter web (Chrome): `flutter run -d chrome --web-port 5000`. Port lain akan ditolak CORS.
- PWS: base URL `https://michael-evan51-pantry-necromancer.pws.cs.ui.ac.id`. Setelah push, pastikan
  `djangorestframework` dan `django-cors-headers` ikut terpasang di PWS.
