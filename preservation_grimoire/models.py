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

    def to_dict(self):
        """Representasi JSON (web service & aplikasi mobile nanti)."""
        return {
            'id': self.pk,
            'title': self.title,
            'category': self.category,
            'category_label': self.get_category_display(),
            'preservation_method': self.preservation_method,
            'content': self.content,
            'smell_indicator': self.smell_indicator,
            'texture_indicator': self.texture_indicator,
            'visual_indicator': self.visual_indicator,
            'author': self.author.username,
            'total_upvotes': self.upvotes.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __str__(self):
        return f"{self.title} - {self.get_category_display()}"