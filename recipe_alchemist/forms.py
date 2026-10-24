from django import forms

from .models import Recipe

DIETS = [
    ('', 'Semua diet'),
    ('vegetarian', 'Vegetarian'),
    ('vegan', 'Vegan'),
    ('gluten free', 'Bebas gluten'),
    ('dairy free', 'Bebas susu'),
]


class SearchForm(forms.Form):
    ingredients = forms.CharField(
        required=False, label='Bahan tambahan',
        widget=forms.TextInput(attrs={'placeholder': 'telur, nasi, bayam'}),
    )
    use_pantry = forms.BooleanField(required=False, initial=True, label='Pakai bahan dari Death Clock')
    max_minutes = forms.IntegerField(required=False, min_value=5, max_value=240, label='Maks. waktu masak (menit)')
    diet = forms.ChoiceField(required=False, choices=DIETS, label='Preferensi diet')


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['title', 'ingredients', 'instructions', 'cook_time_minutes', 'diet', 'notes', 'is_public']
        labels = {'title': 'Judul resep', 'ingredients': 'Bahan', 'instructions': 'Langkah memasak',
                  'cook_time_minutes': 'Waktu masak (menit)', 'diet': 'Preferensi diet',
                  'notes': 'Catatan pribadi', 'is_public': 'Bagikan ke komunitas'}
        help_texts = {'ingredients': 'Satu bahan per baris, mis. "2 butir telur".',
                      'notes': 'Hanya terlihat olehmu. Mis. modifikasi atau pengganti bahan.'}
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'mis. Nasi goreng sisa sayur'}),
            'ingredients': forms.Textarea(attrs={'rows': 5, 'placeholder': '2 butir telur\n1 piring nasi\nbayam'}),
            'instructions': forms.Textarea(attrs={'rows': 6}),
            'cook_time_minutes': forms.NumberInput(attrs={'min': 1, 'max': 1440, 'inputmode': 'numeric'}),
            'diet': forms.Select(choices=[('', 'Tidak ada')] + DIETS[1:]),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_title(self):
        return self.cleaned_data['title'].strip()


class SaveApiRecipeForm(forms.ModelForm):
    """Menyimpan hasil pencarian Spoonacular; data datang dari input tersembunyi di kartu hasil."""

    spoonacular_id = forms.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = ['title', 'spoonacular_id', 'source_url', 'image_url', 'ingredients', 'cook_time_minutes']

    def clean_ingredients(self):
        parts = [p.strip() for p in self.cleaned_data['ingredients'].split('|') if p.strip()]
        if not parts:
            raise forms.ValidationError('Bahan kosong.')
        return '\n'.join(parts)