from django import forms

from .models import PreservationGuide


class PreservationGuideForm(forms.ModelForm):
    """Form panduan. Gaya input mengikuti design system (.pn-form), jadi tidak perlu class per widget."""

    class Meta:
        model = PreservationGuide
        fields = [
            'title',
            'category',
            'preservation_method',
            'content',
            'smell_indicator',
            'texture_indicator',
            'visual_indicator',
        ]
        labels = {
            'title': 'Judul panduan',
            'category': 'Kategori bahan',
            'preservation_method': 'Metode pengawetan',
            'content': 'Langkah pengawetan',
            'smell_indicator': 'Indikator aroma',
            'texture_indicator': 'Indikator tekstur',
            'visual_indicator': 'Indikator tampilan',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Contoh: Membekukan daging ayam tanpa freezer burn'}),
            'preservation_method': forms.TextInput(attrs={'placeholder': 'Contoh: Pembekuan, Acar, Pengeringan'}),
            'content': forms.Textarea(attrs={'rows': 6}),
            'smell_indicator': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Masih layak: … / Sudah rusak: …'}),
            'texture_indicator': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Masih layak: … / Sudah rusak: …'}),
            'visual_indicator': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Masih layak: … / Sudah rusak: …'}),
        }
