from decimal import Decimal

from django import forms
from django.utils import timezone

from graveyard.models import DisposalReason, GraveyardItem


def field_max(field_name):
    """Nilai terbesar yang muat di DecimalField model (mis. max_digits=12, decimal_places=2 -> 9999999999.99)."""
    field = GraveyardItem._meta.get_field(field_name)
    whole = field.max_digits - field.decimal_places
    return Decimal('9' * whole + '.' + '9' * field.decimal_places)


def rupiah(value):
    return f'{int(value):,}'.replace(',', '.')


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
            'reason': forms.Select(attrs={'class': 'pn-input'}),
            'estimated_loss': forms.NumberInput(attrs={
                'class': 'pn-input tabular-nums', 'step': '500', 'min': '0', 'placeholder': 'Contoh: 15000',
            }),
            'weight_g': forms.NumberInput(attrs={
                'class': 'pn-input tabular-nums', 'step': '10', 'min': '0', 'placeholder': 'Contoh: 250',
            }),
            'disposed_at': forms.DateInput(attrs={'class': 'pn-input', 'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={
                'class': 'pn-input', 'rows': 2, 'placeholder': 'Contoh: Mengendap di bagian belakang kulkas...',
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
