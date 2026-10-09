"""Modul 1 · Pantry Death Clock — inventaris bahan makanan pribadi.

Status peluruhan tidak disimpan di database, tetapi dihitung dari tanggal
kedaluwarsa setiap kali dibaca, sehingga selalu sesuai dengan hari ini:

    Flatlining   sisa <= 0 hari (hari ini atau sudah lewat)
    Critical     sisa 1-3 hari
    Stable       sisa > 3 hari
    Resurrected  sudah ditandai diolah/dikonsumsi (resurrected_at terisi)
"""
from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone

CRITICAL_DAYS = 3


class Category(models.TextChoices):
    # Kode sama dengan Preservation Grimoire supaya data antarmodul mudah dihubungkan.
    VEG = 'VEG', 'Sayur & Buah'
    MEAT = 'MEAT', 'Daging & Protein'
    DAIRY = 'DAIRY', 'Produk Olahan Susu'
    GRAIN = 'GRAIN', 'Biji-bijian & Makanan Kering'
    OTHER = 'OTHER', 'Lainnya'


class Storage(models.TextChoices):
    FRIDGE = 'FRIDGE', 'Kulkas'
    FREEZER = 'FREEZER', 'Freezer'
    PANTRY = 'PANTRY', 'Rak dapur'


class Unit(models.TextChoices):
    PIECE = 'pcs', 'buah'
    EGG = 'butir', 'butir'
    PACK = 'pack', 'bungkus'
    BUNCH = 'ikat', 'ikat'
    GRAM = 'g', 'gram'
    KILOGRAM = 'kg', 'kg'
    MILLILITER = 'ml', 'ml'
    LITER = 'l', 'liter'


class Status(models.TextChoices):
    STABLE = 'STABLE', 'Stable'
    CRITICAL = 'CRITICAL', 'Critical'
    FLATLINING = 'FLATLINING', 'Flatlining'
    RESURRECTED = 'RESURRECTED', 'Resurrected'


STATUS_TONES = {
    Status.STABLE: 'ecto',
    Status.CRITICAL: 'ember',
    Status.FLATLINING: 'blood',
    Status.RESURRECTED: 'hex',
}

STATUS_HINTS = {
    Status.STABLE: 'Masih aman disimpan',
    Status.CRITICAL: f'Olah dalam {CRITICAL_DAYS} hari',
    Status.FLATLINING: 'Olah hari ini atau cek kondisinya',
    Status.RESURRECTED: 'Sudah diolah atau dikonsumsi',
}

# Perkiraan kasar umur simpan (hari) bila pengguna tidak mengisi tanggal kedaluwarsa.
# Sengaja konservatif; label kemasan tetap jadi acuan utama.
SHELF_LIFE_DAYS = {
    Category.VEG: {Storage.FRIDGE: 5, Storage.FREEZER: 180, Storage.PANTRY: 3},
    Category.MEAT: {Storage.FRIDGE: 2, Storage.FREEZER: 90, Storage.PANTRY: 0},
    Category.DAIRY: {Storage.FRIDGE: 7, Storage.FREEZER: 60, Storage.PANTRY: 2},
    Category.GRAIN: {Storage.FRIDGE: 180, Storage.FREEZER: 365, Storage.PANTRY: 180},
    Category.OTHER: {Storage.FRIDGE: 7, Storage.FREEZER: 90, Storage.PANTRY: 14},
}


def estimate_expiry(category, storage, purchase_date):
    days = SHELF_LIFE_DAYS.get(category, SHELF_LIFE_DAYS[Category.OTHER]).get(storage, 7)
    return purchase_date + timedelta(days=days)


class PantryItemQuerySet(models.QuerySet):
    def active(self):
        return self.filter(resurrected_at__isnull=True)

    def resurrected(self):
        return self.filter(resurrected_at__isnull=False)

    def with_status(self, status, today=None):
        today = today or timezone.localdate()
        critical_limit = today + timedelta(days=CRITICAL_DAYS)
        if status == Status.RESURRECTED:
            return self.resurrected()
        if status == Status.FLATLINING:
            return self.active().filter(expiry_date__lte=today)
        if status == Status.CRITICAL:
            return self.active().filter(expiry_date__gt=today, expiry_date__lte=critical_limit)
        if status == Status.STABLE:
            return self.active().filter(expiry_date__gt=critical_limit)
        return self.active()

    def status_counts(self, today=None):
        today = today or timezone.localdate()
        critical_limit = today + timedelta(days=CRITICAL_DAYS)
        active = Q(resurrected_at__isnull=True)
        counts = self.aggregate(
            FLATLINING=Count('pk', filter=active & Q(expiry_date__lte=today)),
            CRITICAL=Count('pk', filter=active & Q(expiry_date__gt=today, expiry_date__lte=critical_limit)),
            STABLE=Count('pk', filter=active & Q(expiry_date__gt=critical_limit)),
            RESURRECTED=Count('pk', filter=Q(resurrected_at__isnull=False)),
        )
        counts['ACTIVE'] = counts['FLATLINING'] + counts['CRITICAL'] + counts['STABLE']
        return counts


class PantryItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pantry_items')
    name = models.CharField('nama bahan', max_length=100)
    category = models.CharField('kategori', max_length=10, choices=Category.choices, default=Category.OTHER)
    quantity = models.PositiveIntegerField(
        'jumlah', default=1, validators=[MinValueValidator(1), MaxValueValidator(9999)]
    )
    unit = models.CharField('satuan', max_length=10, choices=Unit.choices, default=Unit.PIECE)
    storage = models.CharField('tempat simpan', max_length=10, choices=Storage.choices, default=Storage.FRIDGE)
    purchase_date = models.DateField('tanggal beli', default=timezone.localdate)
    expiry_date = models.DateField('perkiraan kedaluwarsa')
    expiry_is_estimate = models.BooleanField(default=False)
    notes = models.CharField('catatan', max_length=200, blank=True)
    resurrected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PantryItemQuerySet.as_manager()

    class Meta:
        ordering = ['expiry_date', 'name']
        indexes = [models.Index(fields=['user', 'expiry_date'])]
        verbose_name = 'bahan inventaris'
        verbose_name_plural = 'bahan inventaris'

    def __str__(self):
        return f'{self.name} ({self.user})'

    # ---------- Status dinamis ----------
    @property
    def is_resurrected(self):
        return self.resurrected_at is not None

    @property
    def days_left(self):
        return (self.expiry_date - timezone.localdate()).days

    @property
    def status(self):
        if self.is_resurrected:
            return Status.RESURRECTED
        days = self.days_left
        if days <= 0:
            return Status.FLATLINING
        if days <= CRITICAL_DAYS:
            return Status.CRITICAL
        return Status.STABLE

    @property
    def status_label(self):
        return Status(self.status).label

    @property
    def status_hint(self):
        return STATUS_HINTS[self.status]

    @property
    def tone(self):
        return STATUS_TONES[self.status]

    @property
    def life_percent(self):
        """Sisa umur dalam persen (0-100) untuk meter di kartu."""
        total = (self.expiry_date - self.purchase_date).days
        days = self.days_left
        if days <= 0:
            return 0
        if total <= 0:
            return 100
        return max(0, min(100, round(days / total * 100)))

    @property
    def countdown_label(self):
        days = self.days_left
        if days < 0:
            return f'Lewat {-days} hari'
        if days == 0:
            return 'Hari ini'
        if days == 1:
            return 'Besok'
        return f'{days} hari lagi'

    # ---------- Aksi ----------
    def resurrect(self):
        self.resurrected_at = timezone.now()
        self.save(update_fields=['resurrected_at', 'updated_at'])

    def revive(self):
        self.resurrected_at = None
        self.save(update_fields=['resurrected_at', 'updated_at'])

    def to_dict(self):
        """Representasi JSON (dipakai endpoint JSON dan nanti aplikasi Flutter)."""
        return {
            'id': self.pk,
            'name': self.name,
            'category': self.category,
            'category_label': self.get_category_display(),
            'quantity': self.quantity,
            'unit': self.unit,
            'unit_label': self.get_unit_display(),
            'storage': self.storage,
            'storage_label': self.get_storage_display(),
            'purchase_date': self.purchase_date.isoformat(),
            'expiry_date': self.expiry_date.isoformat(),
            'expiry_is_estimate': self.expiry_is_estimate,
            'days_left': self.days_left,
            'countdown_label': self.countdown_label,
            'status': self.status,
            'status_label': self.status_label,
            'life_percent': self.life_percent,
            'notes': self.notes,
            'is_resurrected': self.is_resurrected,
            'resurrected_at': self.resurrected_at.isoformat() if self.resurrected_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
