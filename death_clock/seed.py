"""Data contoh Death Clock (data sintetis, sesuai ketentuan "data awal" midterm).

Dipakai oleh:
* command ``python manage.py seed_death_clock <username>`` (lokal / server dengan akses shell);
* tombol "Isi data contoh" di halaman Death Clock (akun dengan inventaris kosong, mis. akun demo di PWS).

Tanggal dihitung relatif terhadap hari ini, jadi semua status (Flatlining, Critical, Stable,
Resurrected) selalu muncul kapan pun data dibuat.
"""
import random
from datetime import timedelta

from django.utils import timezone

from death_clock.models import Category, PantryItem, Storage, Unit

DEFAULT_COUNT = 50

# (nama, kategori, satuan, tempat simpan, umur simpan kasar dalam hari) — 50 bahan unik.
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
    ('Kol', Category.VEG, Unit.PIECE, Storage.FRIDGE, 14),
    ('Terong', Category.VEG, Unit.PIECE, Storage.FRIDGE, 5),
    ('Jagung manis', Category.VEG, Unit.PIECE, Storage.FRIDGE, 3),
    ('Mangga', Category.VEG, Unit.PIECE, Storage.PANTRY, 5),
    ('Telur ayam', Category.MEAT, Unit.EGG, Storage.FRIDGE, 21),
    ('Dada ayam', Category.MEAT, Unit.GRAM, Storage.FRIDGE, 2),
    ('Daging sapi giling', Category.MEAT, Unit.GRAM, Storage.FREEZER, 90),
    ('Ikan kembung', Category.MEAT, Unit.PIECE, Storage.FRIDGE, 2),
    ('Udang', Category.MEAT, Unit.GRAM, Storage.FREEZER, 90),
    ('Tahu putih', Category.MEAT, Unit.PIECE, Storage.FRIDGE, 3),
    ('Tempe', Category.MEAT, Unit.PACK, Storage.FRIDGE, 3),
    ('Sosis ayam', Category.MEAT, Unit.PACK, Storage.FRIDGE, 10),
    ('Nugget ayam', Category.MEAT, Unit.PACK, Storage.FREEZER, 60),
    ('Bakso sapi', Category.MEAT, Unit.PACK, Storage.FREEZER, 60),
    ('Susu UHT', Category.DAIRY, Unit.LITER, Storage.FRIDGE, 5),
    ('Yogurt', Category.DAIRY, Unit.PACK, Storage.FRIDGE, 10),
    ('Keju cheddar', Category.DAIRY, Unit.PACK, Storage.FRIDGE, 30),
    ('Keju slice', Category.DAIRY, Unit.PACK, Storage.FRIDGE, 21),
    ('Mentega', Category.DAIRY, Unit.PACK, Storage.FRIDGE, 60),
    ('Krim kental', Category.DAIRY, Unit.MILLILITER, Storage.FRIDGE, 7),
    ('Susu kental manis', Category.DAIRY, Unit.PACK, Storage.PANTRY, 30),
    ('Beras', Category.GRAIN, Unit.KILOGRAM, Storage.PANTRY, 180),
    ('Mi instan', Category.GRAIN, Unit.PACK, Storage.PANTRY, 120),
    ('Roti tawar', Category.GRAIN, Unit.PACK, Storage.PANTRY, 4),
    ('Oatmeal', Category.GRAIN, Unit.PACK, Storage.PANTRY, 180),
    ('Tepung terigu', Category.GRAIN, Unit.KILOGRAM, Storage.PANTRY, 180),
    ('Pasta', Category.GRAIN, Unit.PACK, Storage.PANTRY, 365),
    ('Kacang hijau', Category.GRAIN, Unit.GRAM, Storage.PANTRY, 180),
    ('Sereal jagung', Category.GRAIN, Unit.PACK, Storage.PANTRY, 120),
    ('Nasi sisa semalam', Category.OTHER, Unit.PACK, Storage.FRIDGE, 1),
    ('Sambal botol', Category.OTHER, Unit.PIECE, Storage.FRIDGE, 60),
    ('Kecap manis', Category.OTHER, Unit.PIECE, Storage.PANTRY, 180),
    ('Santan kemasan', Category.OTHER, Unit.PACK, Storage.FRIDGE, 2),
    ('Bumbu rendang instan', Category.OTHER, Unit.PACK, Storage.PANTRY, 90),
    ('Sayur sop sisa', Category.OTHER, Unit.PACK, Storage.FRIDGE, 2),
]

# Setiap bahan ke-10 dibuat sudah "Resurrected" (sudah diolah) supaya status itu ikut terisi.
RESURRECT_EVERY = 10


def seed_items(user, count=DEFAULT_COUNT, seed=None):
    """Buat ``count`` bahan contoh untuk ``user`` dan kembalikan daftar objeknya."""
    rng = random.Random(seed)
    catalog = CATALOG[:]
    rng.shuffle(catalog)  # supaya jumlah kecil pun berisi kategori yang beragam
    now = timezone.now()
    today = timezone.localdate()
    items = []
    for index in range(count):
        name, category, unit, storage, shelf_life = catalog[index % len(catalog)]
        purchase_date = today - timedelta(days=rng.randint(0, 6))
        # Sebar sisa umur supaya semua status (Flatlining/Critical/Stable) muncul.
        expiry_date = max(purchase_date, purchase_date + timedelta(days=shelf_life + rng.randint(-2, 2)))
        resurrected = index % RESURRECT_EVERY == RESURRECT_EVERY - 1
        items.append(PantryItem(
            user=user,
            name=name if index < len(catalog) else f'{name} ({index // len(catalog) + 1})',
            category=category,
            unit=unit,
            storage=storage,
            quantity=rng.choice([100, 250, 500]) if unit in (Unit.GRAM, Unit.MILLILITER) else rng.randint(1, 4),
            purchase_date=purchase_date,
            expiry_date=expiry_date,
            resurrected_at=now - timedelta(hours=rng.randint(1, 72)) if resurrected else None,
        ))
    return PantryItem.objects.bulk_create(items)
