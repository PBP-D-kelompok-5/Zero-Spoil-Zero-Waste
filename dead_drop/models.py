from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.
class ListingStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    RESERVED = "reserved", "Reserved"
    CLAIMED = "claimed", "Claimed"

class FoodListing(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="food_listings")
    reserved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    related_name="food_reservations", null=True, blank=True)
    food_name = models.CharField("Nama makanan", max_length=100)
    description = models.TextField("Kondisi dan deskripsi")
    pickup_location = models.CharField("Alamat / nama lokasi", max_length=255)
    pickup_time = models.DateTimeField("Jadwal penjemputan")
    pickup_notes = models.TextField("Catatan titik temu/penjemputan")
    latitude = models.DecimalField("latitude", max_digits=9, decimal_places=6,
                                   validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField("longitude", max_digits=9, decimal_places=6,
                                   validators=[MinValueValidator(-180), MaxValueValidator(180)])
    status = models.CharField("Status klaim", max_length=9, choices=ListingStatus.choices, default=ListingStatus.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    claimed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.food_name

    class Meta:
        ordering = ["-created_at"]