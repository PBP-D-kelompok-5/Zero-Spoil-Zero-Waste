import re

from django import forms
from django.utils import timezone

from death_clock.models import Category, PantryItem, Status, Storage, Unit, estimate_expiry

MAX_BULK_ITEMS = 30
ESTIMATE_HELP = 'Kosongkan untuk perkiraan otomatis dari kategori dan tempat simpan. Label kemasan tetap jadi acuan utama.'


class DateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%d')
        super().__init__(**kwargs)


def _validate_purchase_date(value):
    if value and value > timezone.localdate():
        raise forms.ValidationError('Tanggal beli tidak boleh di masa depan.')
    return value


def _validate_expiry(form, purchase_date, expiry_date):
    if purchase_date and expiry_date and expiry_date < purchase_date:
        form.add_error('expiry_date', 'Tanggal kedaluwarsa tidak boleh sebelum tanggal beli.')


class PantryItemForm(forms.ModelForm):
    expiry_date = forms.DateField(
        label='Perkiraan kedaluwarsa', required=False, widget=DateInput(), help_text=ESTIMATE_HELP
    )

    class Meta:
        model = PantryItem
        fields = ['name', 'category', 'quantity', 'unit', 'storage', 'purchase_date', 'expiry_date', 'notes']
        labels = {
            'name': 'Nama bahan',
            'category': 'Kategori',
            'quantity': 'Jumlah',
            'unit': 'Satuan',
            'storage': 'Tempat simpan',
            'purchase_date': 'Tanggal beli',
            'notes': 'Catatan (opsional)',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'mis. Bayam', 'autocomplete': 'off'}),
            'quantity': forms.NumberInput(attrs={'min': 1, 'max': 9999, 'inputmode': 'numeric'}),
            'purchase_date': DateInput(),
            'notes': forms.TextInput(attrs={'placeholder': 'mis. sisa setengah ikat, rak paling bawah'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['purchase_date'].initial = timezone.localdate()
        self.fields['purchase_date'].widget.attrs['max'] = timezone.localdate().isoformat()

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_purchase_date(self):
        return _validate_purchase_date(self.cleaned_data.get('purchase_date'))

    def clean(self):
        cleaned = super().clean()
        purchase_date = cleaned.get('purchase_date')
        expiry_date = cleaned.get('expiry_date')

        if expiry_date is None:
            if purchase_date and 'expiry_date' not in self.errors:
                cleaned['expiry_date'] = estimate_expiry(
                    cleaned.get('category', Category.OTHER), cleaned.get('storage', Storage.FRIDGE), purchase_date
                )
                self.instance.expiry_is_estimate = True
        else:
            _validate_expiry(self, purchase_date, expiry_date)
            unchanged = self.instance.pk and expiry_date == self.instance.expiry_date
            self.instance.expiry_is_estimate = bool(unchanged and self.instance.expiry_is_estimate)
        return cleaned


class BulkAddForm(forms.Form):
    """Tambah banyak bahan sekaligus: nama dipisah koma atau baris baru."""

    names = forms.CharField(
        label='Daftar bahan',
        max_length=2000,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'bayam, wortel, tomat, kangkung'}),
        help_text=f'Pisahkan dengan koma atau baris baru (maks. {MAX_BULK_ITEMS} bahan). Semua bahan memakai pengaturan di bawah.',
    )
    category = forms.ChoiceField(label='Kategori', choices=Category.choices, initial=Category.VEG)
    storage = forms.ChoiceField(label='Tempat simpan', choices=Storage.choices, initial=Storage.FRIDGE)
    purchase_date = forms.DateField(label='Tanggal beli', widget=DateInput())
    expiry_date = forms.DateField(label='Perkiraan kedaluwarsa', required=False, widget=DateInput(), help_text=ESTIMATE_HELP)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields['purchase_date'].initial = today
        self.fields['purchase_date'].widget.attrs['max'] = today.isoformat()

    def clean_names(self):
        names, seen = [], set()
        for raw in re.split(r'[,\n;]+', self.cleaned_data['names']):
            name = ' '.join(raw.split())
            if not name or name.casefold() in seen:
                continue
            if len(name) > 100:
                raise forms.ValidationError(f'Nama "{name[:30]}…" terlalu panjang (maks. 100 karakter).')
            seen.add(name.casefold())
            names.append(name)
        if not names:
            raise forms.ValidationError('Tulis minimal satu nama bahan.')
        if len(names) > MAX_BULK_ITEMS:
            raise forms.ValidationError(f'Maksimal {MAX_BULK_ITEMS} bahan sekali tambah (kamu menulis {len(names)}).')
        return names

    def clean_purchase_date(self):
        return _validate_purchase_date(self.cleaned_data.get('purchase_date'))

    def clean(self):
        cleaned = super().clean()
        _validate_expiry(self, cleaned.get('purchase_date'), cleaned.get('expiry_date'))
        return cleaned

    def save(self, user):
        data = self.cleaned_data
        expiry = data['expiry_date']
        is_estimate = expiry is None
        if is_estimate:
            expiry = estimate_expiry(data['category'], data['storage'], data['purchase_date'])
        items = [
            PantryItem(
                user=user,
                name=name,
                category=data['category'],
                storage=data['storage'],
                unit=Unit.PIECE,
                purchase_date=data['purchase_date'],
                expiry_date=expiry,
                expiry_is_estimate=is_estimate,
            )
            for name in data['names']
        ]
        return PantryItem.objects.bulk_create(items)


class FilterForm(forms.Form):
    STATUS_CHOICES = [('', 'Semua aktif')] + [
        (Status.FLATLINING, 'Flatlining'),
        (Status.CRITICAL, 'Critical'),
        (Status.STABLE, 'Stable'),
        (Status.RESURRECTED, 'Resurrected'),
    ]

    q = forms.CharField(label='Cari', required=False, max_length=100)
    status = forms.ChoiceField(label='Status', choices=STATUS_CHOICES, required=False)
    category = forms.ChoiceField(label='Kategori', choices=[('', 'Semua')] + Category.choices, required=False)
    storage = forms.ChoiceField(label='Tempat simpan', choices=[('', 'Semua')] + Storage.choices, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['q'].widget.attrs.update({'placeholder': 'Nama bahan atau catatan…', 'type': 'search'})

    @property
    def values(self):
        """Nilai filter yang valid saja; nilai yang tidak dikenal diabaikan."""
        self.is_valid()
        return {name: self.cleaned_data.get(name) or '' for name in self.fields}


class QuantityForm(forms.Form):
    delta = forms.TypedChoiceField(choices=[('-1', '-1'), ('1', '+1')], coerce=int)
