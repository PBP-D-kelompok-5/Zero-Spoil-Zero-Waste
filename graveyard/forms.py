"""Forms untuk Modul 4 · The Graveyard & Waste Analytics.

Menyediakan:
1. GraveyardItemForm: ModelForm lengkap untuk menambah (Create) dan mengubah (Update)
   catatan bahan makanan yang terbuang.
2. GraveyardMoveForm: ModelForm khusus ritual pemindahan dari inventaris Death Clock.
"""
from decimal import Decimal

from django import forms
from django.utils import timezone

from graveyard.models import Category, DisposalReason, GraveyardItem, Unit


class DateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%d')
        super().__init__(**kwargs)


def _field_max(model_class, field_name):
    field = model_class._meta.get_field(field_name)
    whole = field.max_digits - field.decimal_places
    return Decimal('9' * whole + '.' + '9' * field.decimal_places)


LOSS_MAX = _field_max(GraveyardItem, 'estimated_loss')
WEIGHT_MAX = _field_max(GraveyardItem, 'weight_g')


class GraveyardItemForm(forms.ModelForm):
    """Form pembuatan manual atau pembaharuan catatan nisan bahan makanan."""

    disposed_at = forms.DateField(
        label='Tanggal Dibuang',
        widget=DateInput(attrs={'class': 'pn-input'}),
        initial=timezone.localdate,
        help_text='Tanggal bahan dibuang ke tempat sampah.',
    )
    expiry_date = forms.DateField(
        label='Tanggal Kedaluwarsa (Opsional)',
        required=False,
        widget=DateInput(attrs={'class': 'pn-input'}),
        help_text='Estimasi atau tanggal kedaluwarsa yang tertera pada kemasan.',
    )

    class Meta:
        model = GraveyardItem
        fields = [
            'name',
            'category',
            'reason',
            'quantity',
            'unit',
            'weight_g',
            'estimated_loss',
            'disposed_at',
            'expiry_date',
            'notes',
        ]
        labels = {
            'name': 'Nama Bahan Makanan',
            'category': 'Kategori Pangan',
            'reason': 'Alasan Pembuangan',
            'quantity': 'Jumlah',
            'unit': 'Satuan',
            'weight_g': 'Estimasi Berat (gram)',
            'estimated_loss': 'Estimasi Kerugian (Rp)',
            'notes': 'Catatan Tambahan (Opsional)',
        }
        help_texts = {
            'name': 'Contoh: Susu Sapi UHT, Bayam, Roti Tawar',
            'weight_g': 'Kosongkan atau isi 0 jika tidak tahu (akan diaproksimasi otomatis).',
            'estimated_loss': 'Perkiraan harga beli bahan yang terbuang sia-sia.',
            'notes': 'Contoh: Mengendap di bagian belakang kulkas bersama.',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'mis. Susu UHT Cokelat', 'autocomplete': 'off', 'class': 'pn-input'}),
            'category': forms.Select(attrs={'class': 'pn-input'}),
            'reason': forms.Select(attrs={'class': 'pn-input'}),
            'quantity': forms.NumberInput(attrs={'min': 1, 'max': 9999, 'inputmode': 'numeric', 'class': 'pn-input'}),
            'unit': forms.Select(attrs={'class': 'pn-input'}),
            'weight_g': forms.NumberInput(attrs={'min': 0, 'step': '10', 'class': 'pn-input tabular-nums', 'placeholder': 'mis. 250'}),
            'estimated_loss': forms.NumberInput(attrs={'min': 0, 'step': '500', 'class': 'pn-input tabular-nums', 'placeholder': 'mis. 18000'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Catatan kondisi fisik atau penyebab terbuang...', 'class': 'pn-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Nama bahan makanan wajib diisi.')
        return name

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if not quantity or quantity < 1:
            raise forms.ValidationError('Jumlah bahan minimal 1.')
        return quantity

    def clean_weight_g(self):
        weight = self.cleaned_data.get('weight_g')
        if weight is None:
            return Decimal('0.00')
        if weight < Decimal('0.00'):
            raise forms.ValidationError('Estimasi berat tidak boleh bernilai negatif.')
        if weight > WEIGHT_MAX:
            raise forms.ValidationError(f'Estimasi berat terlalu besar (maksimal {int(WEIGHT_MAX):,}).'.replace(',', '.'))
        return weight

    def clean_estimated_loss(self):
        loss = self.cleaned_data.get('estimated_loss')
        if loss is None:
            return Decimal('0.00')
        if loss < Decimal('0.00'):
            raise forms.ValidationError('Estimasi kerugian tidak boleh bernilai negatif.')
        if loss > LOSS_MAX:
            raise forms.ValidationError(f'Estimasi kerugian terlalu besar (maksimal {int(LOSS_MAX):,}).'.replace(',', '.'))
        return loss

    def clean_disposed_at(self):
        disposed_at = self.cleaned_data.get('disposed_at')
        if disposed_at and disposed_at > timezone.localdate():
            raise forms.ValidationError('Tanggal dibuang tidak boleh di masa depan.')
        return disposed_at


class GraveyardMoveForm(forms.ModelForm):
    """Form khusus konfirmasi pemindahan item dari Death Clock ke Graveyard."""

    disposed_at = forms.DateField(
        label='Tanggal Dibuang',
        widget=DateInput(attrs={'class': 'pn-input'}),
        initial=timezone.localdate,
        help_text='Tanggal bahan dibuang ke tempat sampah.',
    )

    class Meta:
        model = GraveyardItem
        fields = [
            'reason',
            'estimated_loss',
            'weight_g',
            'disposed_at',
            'notes',
        ]
        labels = {
            'reason': 'Alasan Pembusukan atau Pembuangan',
            'estimated_loss': 'Estimasi Kerugian (Rp)',
            'weight_g': 'Estimasi Berat (gram)',
            'notes': 'Catatan Tambahan (Opsional)',
        }
        widgets = {
            'reason': forms.Select(attrs={'class': 'pn-input', 'id': 'reason'}),
            'estimated_loss': forms.NumberInput(attrs={
                'min': 0,
                'step': '500',
                'class': 'pn-input tabular-nums',
                'id': 'estimated_loss',
                'placeholder': 'Contoh: 15000',
            }),
            'weight_g': forms.NumberInput(attrs={
                'min': 0,
                'step': '10',
                'class': 'pn-input tabular-nums',
                'id': 'weight_g',
                'placeholder': 'Contoh: 250',
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'class': 'pn-input',
                'id': 'notes',
                'placeholder': 'Contoh: Mengendap di bagian belakang kulkas...',
            }),
        }

    def clean_weight_g(self):
        weight = self.cleaned_data.get('weight_g')
        if weight is None:
            return Decimal('0.00')
        if weight < Decimal('0.00'):
            raise forms.ValidationError('Estimasi berat tidak boleh bernilai negatif.')
        if weight > WEIGHT_MAX:
            raise forms.ValidationError(f'Estimasi berat terlalu besar (maksimal {int(WEIGHT_MAX):,}).'.replace(',', '.'))
        return weight

    def clean_estimated_loss(self):
        loss = self.cleaned_data.get('estimated_loss')
        if loss is None:
            return Decimal('0.00')
        if loss < Decimal('0.00'):
            raise forms.ValidationError('Estimasi kerugian tidak boleh bernilai negatif.')
        if loss > LOSS_MAX:
            raise forms.ValidationError(f'Estimasi kerugian terlalu besar (maksimal {int(LOSS_MAX):,}).'.replace(',', '.'))
        return loss

    def clean_disposed_at(self):
        disposed_at = self.cleaned_data.get('disposed_at')
        if disposed_at and disposed_at > timezone.localdate():
            raise forms.ValidationError('Tanggal dibuang tidak boleh di masa depan.')
        return disposed_at
