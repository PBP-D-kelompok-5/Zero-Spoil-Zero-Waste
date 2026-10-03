from django import forms
from .models import PreservationGuide

class PreservationGuideForm(forms.ModelForm):
    class Meta:
        model = PreservationGuide
        fields = [
            'title', 
            'category', 
            'preservation_method', 
            'content', 
            'smell_indicator', 
            'texture_indicator', 
            'visual_indicator'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg', 'placeholder': 'Judul Panduan'}),
            'category': forms.Select(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'preservation_method': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg', 'placeholder': 'Metode (misal: Pembekuan)'}),
            'content': forms.Textarea(attrs={'class': 'w-full p-2 border rounded-lg', 'rows': 4}),
            'smell_indicator': forms.Textarea(attrs={'class': 'w-full p-2 border rounded-lg', 'rows': 2}),
            'texture_indicator': forms.Textarea(attrs={'class': 'w-full p-2 border rounded-lg', 'rows': 2}),
            'visual_indicator': forms.Textarea(attrs={'class': 'w-full p-2 border rounded-lg', 'rows': 2}),
        }