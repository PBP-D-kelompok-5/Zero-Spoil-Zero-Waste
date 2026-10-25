"""Forms untuk Modul 4 · The Graveyard & Waste Analytics.

Menyediakan:
1. BuryForm / GraveyardMoveForm: Form konfirmasi ritual pemindahan dari Death Clock ke Graveyard.
2. GraveyardItemForm: ModelForm lengkap untuk menambah (Create) dan mengubah (Update)
   catatan bahan makanan yang terbuang secara langsung.
"""
from decimal import Decimal

from django import forms
from django.utils import timezone

from graveyard.models import Category, DisposalReason, GraveyardItem, Unit


def field_max(field_name):
    """Nilai terbesar yang muat di DecimalField model (mis. max_digits=12, decimal_places=2 -> 9999999999.99)."""
    field = GraveyardItem._meta.get_field(field_name)
    whole = field.max_digits - field.decimal_places
    return Decimal('9' * whole + '.' + '9' * field.decimal_places)


def rupiah(value):
    return f'{int(value):,}'.replace(',', '.')


LOSS_MAX = field_max('estimated_loss')
WEIGHT_MAX = field_max('weight_g')


class DateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%d')
        super().__init__(**kwargs)


class BuryForm(forms.ModelForm):
    """Form "kubur": memindahkan bahan dari Death Clock ke Graveyard.

    Nama, kategori, kuantitas, satuan, dan tanggal kedaluwarsa diambil dari bahan Death Clock
    di view; form ini hanya menerima isian pengguna dan memvalidasinya.
    """

    LOSS_MAX = field_max('estimated_loss')
    WEIGHT_MAX = field_max('weight_g')

    class Meta:
        model = GraveyardItem
        fields = ['reason', 'estimated_loss', 'weight_g', 'disposed_at', 'notes']
        labels = {
            'reason': 'Alasan pembusukan atau pembuangan',
            'estimated_loss': 'Estimasi kerugian (Rp)',
            'weight_g': 'Estimasi berat (gram)',
            'disposed_at': 'Tanggal dibuang',
            'notes': 'Catatan tambahan (opsional)',
        }
        help_texts = {
            'reason': 'Pilih alasan paling dominan mengapa bahan ini gagal dikonsumsi.',
            'estimated_loss': 'Perkiraan harga beli bahan ini. Kosongkan jika tidak tahu.',
            'weight_g': 'Kosongkan jika tidak tahu.',
        }
        widgets = {
            'reason': forms.Select(attrs={'class': 'pn-input', 'id': 'reason'}),
            'estimated_loss': forms.NumberInput(attrs={
                'class': 'pn-input tabular-nums', 'step': '500', 'min': '0', 'placeholder': 'Contoh: 15000', 'id': 'estimated_loss',
            }),
            'weight_g': forms.NumberInput(attrs={
                'class': 'pn-input tabular-nums', 'step': '10', 'min': '0', 'placeholder': 'Contoh: 250', 'id': 'weight_g',
            }),
            'disposed_at': forms.DateInput(attrs={'class': 'pn-input', 'type': 'date', 'id': 'disposed_at'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={
                'class': 'pn-input', 'rows': 2, 'placeholder': 'Contoh: Mengendap di bagian belakang kulkas...', 'id': 'notes',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hanya alasan yang wajib; isian lain punya nilai bawaan yang masuk akal.
        for name in ('disposed_at', 'notes'):
            self.fields[name].required = False
        self.fields['reason'].initial = DisposalReason.EXPIRED
        self.fields['disposed_at'].initial = timezone.localdate()
        # Batas angka dibuat eksplisit agar pesannya jelas (bukan "jumlah digit lebih dari 12").
        for name, label, maximum in (
            ('estimated_loss', 'Estimasi kerugian', self.LOSS_MAX),
            ('weight_g', 'Estimasi berat', self.WEIGHT_MAX),
        ):
            old = self.fields[name]
            self.fields[name] = forms.DecimalField(
                label=old.label,
                help_text=old.help_text,
                widget=old.widget,
                required=False,
                min_value=Decimal('0'),
                max_value=maximum,
                decimal_places=2,
                error_messages={
                    'min_value': f'{label} tidak boleh negatif.',
                    'max_value': f'{label} terlalu besar (maksimal {rupiah(maximum)}).',
                    'invalid': f'{label} harus berupa angka.',
                },
            )
            self.fields[name].widget.attrs['max'] = str(maximum)

    def clean_estimated_loss(self):
        return self.cleaned_data.get('estimated_loss') or Decimal('0.00')

    def clean_weight_g(self):
        return self.cleaned_data.get('weight_g') or Decimal('0.00')

    def clean_disposed_at(self):
        value = self.cleaned_data.get('disposed_at') or timezone.localdate()
        if value > timezone.localdate():
            raise forms.ValidationError('Tanggal dibuang tidak boleh di masa depan.')
        return value

    def clean_notes(self):
        return (self.cleaned_data.get('notes') or '').strip()


# Alias untuk keselarasan dengan penamaan test dan modul lain
GraveyardMoveForm = BuryForm


class GraveyardItemForm(forms.ModelForm):
    """Form pembuatan manual (Create) atau pembaharuan (Update) catatan nisan bahan makanan."""

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
            raise forms.ValidationError(f'Estimasi berat terlalu besar (maksimal {rupiah(WEIGHT_MAX)}).')
        return weight

    def clean_estimated_loss(self):
        loss = self.cleaned_data.get('estimated_loss')
        if loss is None:
            return Decimal('0.00')
        if loss < Decimal('0.00'):
            raise forms.ValidationError('Estimasi kerugian tidak boleh bernilai negatif.')
        if loss > LOSS_MAX:
            raise forms.ValidationError(f'Estimasi kerugian terlalu besar (maksimal {rupiah(LOSS_MAX)}).')
        return loss

    def clean_disposed_at(self):
        disposed_at = self.cleaned_data.get('disposed_at')
        if disposed_at and disposed_at > timezone.localdate():
            raise forms.ValidationError('Tanggal dibuang tidak boleh di masa depan.')
        return disposed_at
