from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Recipe(models.Model):
    class Source(models.TextChoices):
        CUSTOM = 'CUSTOM', 'Resep kustom'
        SPOONACULAR = 'SPOONACULAR', 'Spoonacular'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recipes')
    title = models.CharField('judul', max_length=200)
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.CUSTOM)
    spoonacular_id = models.PositiveIntegerField(null=True, blank=True)
    source_url = models.URLField(blank=True, max_length=500)
    image_url = models.URLField(blank=True, max_length=500)
    ingredients = models.TextField('bahan')
    instructions = models.TextField('langkah memasak', blank=True)
    cook_time_minutes = models.PositiveIntegerField(
        'waktu masak (menit)', null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
    )
    diet = models.CharField('preferensi diet', max_length=50, blank=True)
    notes = models.TextField('catatan pribadi', blank=True)
    is_public = models.BooleanField('bagikan ke komunitas', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            # Null spoonacular_id (custom recipes) never collides; each API recipe is saved once per user.
            models.UniqueConstraint(fields=['user', 'spoonacular_id'], name='unique_saved_spoonacular_recipe'),
        ]

    def __str__(self):
        return f'{self.title} ({self.user})'

    @property
    def ingredient_list(self):
        return [line.strip() for line in self.ingredients.splitlines() if line.strip()]