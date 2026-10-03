from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

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


# Konten contoh untuk rancangan awal modul. Artikel komunitas akan dipindahkan ke
# model database pada tahap implementasi CRUD.
GRIMOIRE_GUIDES = [
    {
        'title': 'Kenali label tanggal pada kemasan',
        'category': 'Produk kemasan',
        'method': 'Panduan dasar',
        'description': 'Mulai dari petunjuk penyimpanan dan tanggal pada label. Arti label dapat berbeda menurut produk dan aturan setempat.',
        'icon': '🏷️',
        'tone': 'frost',
        'time': '4 menit baca',
    },
    {
        'title': 'Rapikan kulkas untuk bahan yang mudah rusak',
        'category': 'Sayur & buah',
        'method': 'Penyimpanan',
        'description': 'Rancang kebiasaan penyimpanan yang rapi: pisahkan bahan, cek kondisi kemasan, dan ikuti petunjuk produk.',
        'icon': '🥬',
        'tone': 'ecto',
        'time': '5 menit baca',
    },
    {
        'title': 'Bekukan bahan dengan rencana pakai',
        'category': 'Semua bahan',
        'method': 'Pembekuan',
        'description': 'Beri label isi dan tanggal, gunakan wadah yang sesuai, lalu ikuti panduan penyimpanan tepercaya untuk jenis bahanmu.',
        'icon': '❄️',
        'tone': 'hex',
        'time': '3 menit baca',
    },
    {
        'title': 'Bedakan tanda penurunan mutu dan keamanan pangan',
        'category': 'Panduan keamanan',
        'method': 'Smell Test',
        'description': 'Bau atau tampilan yang tidak normal adalah alasan untuk berhenti dan memeriksa panduan keamanan yang sesuai.',
        'icon': '🧪',
        'tone': 'ember',
        'time': '6 menit baca',
    },
]


def preservation_grimoire(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    method = request.GET.get('method', '').strip()
    guides = GRIMOIRE_GUIDES

    if query:
        query_lower = query.casefold()
        guides = [guide for guide in guides if query_lower in ' '.join((
            guide['title'], guide['category'], guide['method'], guide['description']
        )).casefold()]
    if category:
        guides = [guide for guide in guides if guide['category'] == category]
    if method:
        guides = [guide for guide in guides if guide['method'] == method]

    return render(request, 'main/grimoire.html', {
        'guides': guides,
        'query': query,
        'selected_category': category,
        'selected_method': method,
        'categories': sorted({guide['category'] for guide in GRIMOIRE_GUIDES}),
        'methods': sorted({guide['method'] for guide in GRIMOIRE_GUIDES}),
    })


def get_next_url(request):
    """Ambil ?next= hanya jika mengarah ke situs ini sendiri."""
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return 'main:show_main'


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
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f'Selamat datang kembali, {user.username}!')
        return redirect(get_next_url(request))

    return render(request, 'main/auth/login.html', {'form': form, 'next': request.GET.get('next', '')})


@require_POST
def logout_user(request):
    logout(request)
    messages.info(request, 'Kamu sudah keluar. Sampai jumpa lagi!')
    return redirect('main:show_main')
