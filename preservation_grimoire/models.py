from django.db import models
from django.contrib.auth.models import User

class PreservationGuide(models.Model):
    CATEGORY_CHOICES = [
        ('VEG', 'Sayur & Buah'),
        ('MEAT', 'Daging & Protein'),
        ('DAIRY', 'Produk Olahan Susu'),
        ('GRAIN', 'Biji-bijian & Makanan Kering'),
        ('OTHER', 'Lainnya'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='preservation_guides')
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='OTHER')
    preservation_method = models.CharField(max_length=100, help_text="Contoh: Freezing, Pickling, Dehydration")
    
    # Panduan Pengawetan
    content = models.TextField(help_text="Langkah-langkah pengawetan bahan makanan.")
    
    # Indikator Uji Sensori (Smell Test)
    smell_indicator = models.TextField(help_text="Ciri-ciri aroma bahan yang masih layak vs sudah rusak.")
    texture_indicator = models.TextField(help_text="Perubahan tekstur yang perlu diwaspadai.")
    visual_indicator = models.TextField(help_text="Perubahan warna atau tampilan fisik (misal: jamur).")
    
    upvotes = models.ManyToManyField(User, related_name='upvoted_guides', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def total_upvotes(self):
        return self.upvotes.count()

    def __str__(self):
        return f"{self.title} - {self.get_category_display()}"