"""Isi inventaris contoh untuk satu akun, mis. untuk demo atau pengecekan tampilan.

    python manage.py seed_death_clock <username>              # 50 bahan
    python manage.py seed_death_clock <username> --count 20 --clear

Tanpa akses shell (mis. di PWS): login ke akun tersebut lalu klik "Isi data contoh"
di halaman Death Clock yang masih kosong. Keduanya memakai death_clock.seed.seed_items.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from death_clock.models import PantryItem
from death_clock.seed import DEFAULT_COUNT, seed_items


class Command(BaseCommand):
    help = 'Isi inventaris Death Clock contoh untuk satu akun yang sudah ada.'

    def add_arguments(self, parser):
        parser.add_argument('username', help='Akun pemilik inventaris (harus sudah terdaftar).')
        parser.add_argument('--count', type=int, default=DEFAULT_COUNT, help=f'Jumlah bahan (1-200, bawaan {DEFAULT_COUNT}).')
        parser.add_argument('--clear', action='store_true', help='Hapus inventaris akun ini terlebih dahulu.')
        parser.add_argument('--seed', type=int, default=None, help='Seed acak agar hasilnya bisa diulang.')

    def handle(self, *args, username, count, clear, seed, **options):
        if not 1 <= count <= 200:
            raise CommandError('--count harus di antara 1 dan 200.')
        try:
            user = get_user_model().objects.get(username=username)
        except get_user_model().DoesNotExist:
            raise CommandError(f'Akun "{username}" tidak ditemukan. Daftarkan dulu lewat halaman /register/.')

        if clear:
            deleted, _ = PantryItem.objects.filter(user=user).delete()
            self.stdout.write(f'{deleted} bahan lama dihapus.')

        items = seed_items(user, count=count, seed=seed)
        self.stdout.write(self.style.SUCCESS(f'{len(items)} bahan ditambahkan ke inventaris {username}.'))
