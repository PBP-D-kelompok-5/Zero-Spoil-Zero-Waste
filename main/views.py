import math

from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from main.auth import LoginThrottle, safe_next_url
from main.forms import LoginForm, RegisterForm

MODULES = [
    {
        'slug': 'death-clock',
        'name': 'Pantry Death Clock',
        'description': 'Inventaris bahan makanan pribadi dengan status kedaluwarsa Stable, Critical, dan Flatlining.',
        'owner': 'Michael Evan Putra Nugroho',
        'tone': 'ecto',
    },
    {
        'slug': 'recipe-alchemist',
        'name': 'Recipe Alchemist',
        'description': 'Resep penyelamat dari sisa bahan lewat Spoonacular API.',
        'owner': 'Nuno Mikael Nugroho',
        'tone': 'hex',
    },
    {
        'slug': 'dead-drop',
        'name': 'The Dead Drop',
        'description': 'Berbagi surplus bahan makanan dengan tetangga kost, lengkap dengan peta OpenStreetMap.',
        'owner': 'Joshua Carnsyn Suyanto Sidik',
        'tone': 'ember',
    },
    {
        'slug': 'graveyard',
        'name': 'The Graveyard',
        'description': 'Pencatatan bahan yang terbuang serta analitik kerugian uang dan emisi CO₂.',
        'owner': 'Adam Wahyu Syaputra',
        'tone': 'blood',
    },
    {
        'slug': 'grimoire',
        'name': 'Preservation Grimoire',
        'description': 'Wiki teknik pengawetan dan panduan smell test dari komunitas.',
        'owner': 'Muhammad Syarifudin',
        'tone': 'frost',
    },
]


# Contoh isi kartu Death Clock di landing page (ilustrasi, bukan data pengguna)
PREVIEW_ITEMS = [
    {'name': 'Bayam', 'category': 'Sayur', 'days_left': 0, 'percent': 6, 'status': 'Flatlining', 'tone': 'blood'},
    {'name': 'Susu UHT', 'category': 'Produk Susu', 'days_left': 2, 'percent': 28, 'status': 'Critical', 'tone': 'ember'},
    {'name': 'Telur ayam', 'category': 'Protein', 'days_left': 12, 'percent': 82, 'status': 'Stable', 'tone': 'ecto'},
]


def show_main(request):
    context = {
        'modules': MODULES,
        'preview_items': PREVIEW_ITEMS,
    }
    return render(request, 'main/home.html', context)


def get_next_url(request):
    """Ambil ?next= hanya jika mengarah ke situs ini sendiri."""
    return safe_next_url(request, 'main:show_main')


def register(request):
    if request.user.is_authenticated:
        return redirect('main:show_main')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Akun {user.username} berhasil dibuat. Selamat datang, Necromancer!')
        return redirect(get_next_url(request))

    return render(request, 'main/auth/register.html', {'form': form, 'next': request.GET.get('next', '')})


def login_user(request):
    if request.user.is_authenticated:
        return redirect('main:show_main')

    form = LoginForm(request, data=request.POST or None)
    status = 200
    if request.method == 'POST':
        throttle = LoginThrottle(request, request.POST.get('username'))
        wait = throttle.blocked_for()
        if wait:
            # Terkunci: password tidak diperiksa sama sekali agar tebakan beruntun tidak berguna.
            form = LoginForm(request, initial={'username': request.POST.get('username', '')})
            messages.error(request, f'Terlalu banyak percobaan masuk yang gagal. Coba lagi dalam {math.ceil(wait / 60)} menit.')
            status = 429
        elif form.is_valid():
            throttle.reset()
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Selamat datang kembali, {user.username}!')
            return redirect(get_next_url(request))
        else:
            throttle.failed()

    context = {'form': form, 'next': request.GET.get('next', '')}
    return render(request, 'main/auth/login.html', context, status=status)


@require_POST
def logout_user(request):
    logout(request)
    messages.info(request, 'Kamu sudah keluar. Sampai jumpa lagi!')
    return redirect('main:show_main')
