"""Isi inventaris contoh untuk satu akun, mis. untuk demo atau pengecekan tampilan.

    python manage.py seed_death_clock <username>              # 50 bahan
    python manage.py seed_death_clock <username> --count 20 --clear
"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from death_clock.models import Category, PantryItem, Storage, Unit

# (nama, kategori, satuan, tempat simpan, umur simpan kasar dalam hari)
CATALOG = [
    ('Bayam', Category.VEG, Unit.BUNCH, Storage.FRIDGE, 3),
    ('Kangkung', Category.VEG, Unit.BUNCH, Storage.FRIDGE, 3),
    ('Sawi hijau', Category.VEG, Unit.BUNCH, Storage.FRIDGE, 4),
    ('Wortel', Category.VEG, Unit.PIECE, Storage.FRIDGE, 14),
    ('Tomat', Category.VEG, Unit.PIECE, Storage.FRIDGE, 7),
    ('Cabai rawit', Category.VEG, Unit.GRAM, Storage.FRIDGE, 7),
    ('Bawang merah', Category.VEG, Unit.GRAM, Storage.PANTRY, 30),
    ('Bawang putih', Category.VEG, Unit.GRAM, Storage.PANTRY, 60),
    ('Kentang', Category.VEG, Unit.KILOGRAM, Storage.PANTRY, 30),
    ('Pisang', Category.VEG, Unit.PIECE, Storage.PANTRY, 4),
    ('Apel', Category.VEG, Unit.PIECE, Storage.FRIDGE, 21),
    ('Jeruk', Category.VEG, Unit.PIECE, Storage.FRIDGE, 14),
    ('Brokoli', Category.VEG, Unit.PIECE, Storage.FRIDGE, 5),
    ('Tauge', Category.VEG, Unit.GRAM, Storage.FRIDGE, 2),
    ('Daun bawang', Category.VEG, Unit.BUNCH, Storage.FRIDGE, 7),
    ('Telur ayam', Category.MEAT, Unit.EGG, Storage.FRIDGE, 21),
    ('Dada ayam', Category.MEAT, Unit.GRAM, Storage.FRIDGE, 2),
    ('Daging sapi giling', Category.MEAT, Unit.GRAM, Storage.FREEZER, 90),
    ('Ikan kembung', Category.MEAT, Unit.PIECE, Storage.FRIDGE, 2),
    ('Udang', Category.MEAT, Unit.GRAM, Storage.FREEZER, 90),
    ('Tahu putih', Category.MEAT, Unit.PIECE, Storage.FRIDGE, 3),
    ('Tempe', Category.MEAT, Unit.PACK, Storage.FRIDGE, 3),
    ('Sosis ayam', Category.MEAT, Unit.PACK, Storage.FRIDGE, 10),
    ('Nugget ayam', Category.MEAT, Unit.PACK, Storage.FREEZER, 60),
    ('Susu UHT', Category.DAIRY, Unit.LITER, Storage.FRIDGE, 5),
    ('Yogurt', Category.DAIRY, Unit.PACK, Storage.FRIDGE, 10),
    ('Keju cheddar', Category.DAIRY, Unit.PACK, Storage.FRIDGE, 30),
    ('Mentega', Category.DAIRY, Unit.PACK, Storage.FRIDGE, 60),
    ('Susu kental manis', Category.DAIRY, Unit.PACK, Storage.PANTRY, 30),
    ('Beras', Category.GRAIN, Unit.KILOGRAM, Storage.PANTRY, 180),
    ('Mi instan', Category.GRAIN, Unit.PACK, Storage.PANTRY, 120),
    ('Roti tawar', Category.GRAIN, Unit.PACK, Storage.PANTRY, 4),
    ('Oatmeal', Category.GRAIN, Unit.PACK, Storage.PANTRY, 180),
    ('Tepung terigu', Category.GRAIN, Unit.KILOGRAM, Storage.PANTRY, 180),
    ('Pasta', Category.GRAIN, Unit.PACK, Storage.PANTRY, 365),
    ('Kacang hijau', Category.GRAIN, Unit.GRAM, Storage.PANTRY, 180),
    ('Nasi sisa semalam', Category.OTHER, Unit.PACK, Storage.FRIDGE, 1),
    ('Sambal botol', Category.OTHER, Unit.PIECE, Storage.FRIDGE, 60),
    ('Kecap manis', Category.OTHER, Unit.PIECE, Storage.PANTRY, 180),
    ('Santan kemasan', Category.OTHER, Unit.PACK, Storage.FRIDGE, 2),
    ('Bumbu rendang instan', Category.OTHER, Unit.PACK, Storage.PANTRY, 90),
    ('Sayur sop sisa', Category.OTHER, Unit.PACK, Storage.FRIDGE, 2),
]


class Command(BaseCommand):
    help = 'Isi inventaris Death Clock contoh untuk satu akun yang sudah ada.'

    def add_arguments(self, parser):
        parser.add_argument('username', help='Akun pemilik inventaris (harus sudah terdaftar).')
        parser.add_argument('--count', type=int, default=50, help='Jumlah bahan (1-200, bawaan 50).')
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

        rng = random.Random(seed)
        catalog = CATALOG[:]
        rng.shuffle(catalog)  # supaya --count kecil pun berisi kategori yang beragam
        today = timezone.localdate()
        items = []
        for index in range(count):
            name, category, unit, storage, shelf_life = catalog[index % len(catalog)]
            bought_days_ago = rng.randint(0, 6)
            purchase_date = today - timedelta(days=bought_days_ago)
            # Sebar sisa umur supaya semua status (Flatlining/Critical/Stable) muncul.
            jitter = rng.randint(-2, 2)
            expiry_date = max(purchase_date, purchase_date + timedelta(days=shelf_life + jitter))
            items.append(PantryItem(
                user=user,
                name=name if index < len(catalog) else f'{name} ({index // len(catalog) + 1})',
                category=category,
                unit=unit,
                storage=storage,
                quantity=rng.choice([100, 250, 500]) if unit in (Unit.GRAM, Unit.MILLILITER) else rng.randint(1, 4),
                purchase_date=purchase_date,
                expiry_date=expiry_date,
            ))
        PantryItem.objects.bulk_create(items)
        self.stdout.write(self.style.SUCCESS(f'{len(items)} bahan ditambahkan ke inventaris {username}.'))
