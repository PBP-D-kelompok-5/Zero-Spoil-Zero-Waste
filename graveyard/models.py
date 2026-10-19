"""Modul 4 · The Graveyard & Waste Analytics — Pencatatan Limbah & Pelacak Dampak.

Mencatat bahan makanan yang gagal diselamatkan/berakhir di tempat sampah (Graveyard),
lengkap dengan alasan kegagalan konsumsi, estimasi berat, kerugian finansial (Rp),
serta estimasi jejak karbon (CO₂).
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Category(models.TextChoices):
    # Selaras dengan death_clock dan preservation_grimoire
    VEG = 'VEG', 'Sayur & Buah'
    MEAT = 'MEAT', 'Daging & Protein'
    DAIRY = 'DAIRY', 'Produk Olahan Susu'
    GRAIN = 'GRAIN', 'Biji-bijian & Makanan Kering'
    OTHER = 'OTHER', 'Lainnya'


class Unit(models.TextChoices):
    # Selaras dengan satuan pada death_clock
    PIECE = 'pcs', 'buah'
    EGG = 'butir', 'butir'
    PACK = 'pack', 'bungkus'
    BUNCH = 'ikat', 'ikat'
    GRAM = 'g', 'gram'
    KILOGRAM = 'kg', 'kg'
    MILLILITER = 'ml', 'ml'
    LITER = 'l', 'liter'


class DisposalReason(models.TextChoices):
    EXPIRED = 'EXPIRED', 'Sudah melewati tanggal kedaluwarsa'
    FORGOTTEN = 'FORGOTTEN', 'Terlupa di sudut kulkas / rak'
    SPOILED_EARLY = 'SPOILED_EARLY', 'Membusuk sebelum tanggal kedaluwarsa'
    SMELL_TEXTURE = 'SMELL_TEXTURE', 'Gagal uji sensori (bau tidak sedap / tekstur rusak)'
    MOLD = 'MOLD', 'Berjamur / terkontaminasi'
    OVERCOOKED = 'OVERCOOKED', 'Porsi masak berlebih / sisa makanan tidak habis'
    OTHER = 'OTHER', 'Alasan lainnya'


# Faktor emisi CO₂ (kg CO₂e per kg limbah makanan) menurut kategori pangan
CARBON_FACTORS_PER_KG = {
    Category.VEG: Decimal('2.0'),
    Category.MEAT: Decimal('20.0'),
    Category.DAIRY: Decimal('8.0'),
    Category.GRAIN: Decimal('2.5'),
    Category.OTHER: Decimal('3.0'),
}

# Estimasi konversi gram per satuan jika berat gram tidak diisi langsung
DEFAULT_UNIT_WEIGHT_GRAMS = {
    Unit.PIECE: Decimal('150.0'),
    Unit.EGG: Decimal('60.0'),
    Unit.PACK: Decimal('250.0'),
    Unit.BUNCH: Decimal('200.0'),
    Unit.GRAM: Decimal('1.0'),
    Unit.KILOGRAM: Decimal('1000.0'),
    Unit.MILLILITER: Decimal('1.0'),
    Unit.LITER: Decimal('1000.0'),
}


class GraveyardItemQuerySet(models.QuerySet):
    def total_loss(self):
        """Total akumulasi kerugian uang (Rp)."""
        aggregate = self.aggregate(total=models.Sum('estimated_loss'))
        return aggregate['total'] or Decimal('0.00')

    def total_weight_kg(self):
        """Total estimasi berat limbah dalam kilogram."""
        aggregate = self.aggregate(total=models.Sum('weight_g'))
        total_g = aggregate['total'] or Decimal('0.00')
        return (total_g / Decimal('1000.0')).quantize(Decimal('0.01'))

    def for_user(self, user):
        return self.filter(user=user)


class GraveyardItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='graveyard_items',
        verbose_name='Pengguna',
    )
    name = models.CharField(
        max_length=120,
        verbose_name='Nama Item Makanan',
        help_text='Nama bahan makanan yang terbuang (contoh: Susu Sapi UHT, Bayam)',
    )
    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        default=Category.OTHER,
        verbose_name='Kategori',
    )
    reason = models.CharField(
        max_length=30,
        choices=DisposalReason.choices,
        default=DisposalReason.EXPIRED,
        verbose_name='Alasan Pembuangan',
    )
    notes = models.TextField(
        blank=True,
        default='',
        verbose_name='Catatan Tambahan',
        help_text='Catatan penyebab atau kondisi bahan saat dibuang',
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Tanggal Kedaluwarsa',
        help_text='Estimasi atau tanggal kedaluwarsa tercatat pada bahan',
    )
    disposed_at = models.DateField(
        default=timezone.localdate,
        verbose_name='Tanggal Dibuang',
        help_text='Tanggal bahan dibuang ke tempat sampah',
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Jumlah',
    )
    unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
        default=Unit.PIECE,
        verbose_name='Satuan',
    )
    weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Estimasi Berat (gram)',
        help_text='Estimasi berat bahan yang terbuang dalam satuan gram',
    )
    estimated_loss = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Estimasi Kerugian (Rp)',
        help_text='Perkiraan harga beli atau kerugian rupiah akibat terbuang',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Dibuat Pada')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Diperbarui Pada')

    objects = GraveyardItemQuerySet.as_manager()

    class Meta:
        ordering = ['-disposed_at', '-created_at']
        verbose_name = 'Graveyard Item'
        verbose_name_plural = 'Graveyard Items'

    def __str__(self):
        return f"{self.name} ({self.get_category_display()}) - {self.get_reason_display()}"

    @property
    def effective_weight_grams(self):
        """Mengembalikan berat dalam gram. Jika belum diisi (> 0), hitung aproksimasi dari satuan."""
        if self.weight_g and self.weight_g > 0:
            return self.weight_g
        per_unit = DEFAULT_UNIT_WEIGHT_GRAMS.get(self.unit, Decimal('100.0'))
        return (Decimal(self.quantity) * per_unit).quantize(Decimal('0.01'))

    @property
    def effective_weight_kg(self):
        """Berat efektif dalam satuan kilogram."""
        return (self.effective_weight_grams / Decimal('1000.0')).quantize(Decimal('0.01'))

    @property
    def estimated_carbon_kg(self):
        """Estimasi jejak karbon (kg CO₂e) dari bahan yang terbuang."""
        factor = CARBON_FACTORS_PER_KG.get(self.category, Decimal('3.0'))
        weight_kg = self.effective_weight_kg
        return (weight_kg * factor).quantize(Decimal('0.01'))

    def to_dict(self):
        """Serialisasi ke dictionary/JSON untuk integrasi API dan analitik."""
        return {
            'id': self.pk,
            'name': self.name,
            'category': self.category,
            'category_label': self.get_category_display(),
            'reason': self.reason,
            'reason_label': self.get_reason_display(),
            'notes': self.notes,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'disposed_at': self.disposed_at.isoformat() if self.disposed_at else None,
            'quantity': self.quantity,
            'unit': self.unit,
            'unit_label': self.get_unit_display(),
            'weight_g': float(self.weight_g),
            'effective_weight_kg': float(self.effective_weight_kg),
            'estimated_loss': float(self.estimated_loss),
            'estimated_carbon_kg': float(self.estimated_carbon_kg),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
