from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator

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

    def to_dict(self):
        """Representasi JSON (web service & aplikasi mobile nanti)."""
        return {
            'id': self.pk,
            'food_name': self.food_name,
            'description': self.description,
            'pickup_location': self.pickup_location,
            'pickup_time': self.pickup_time.isoformat() if self.pickup_time else None,
            'pickup_notes': self.pickup_notes,
            'latitude': float(self.latitude),
            'longitude': float(self.longitude),
            'status': self.status,
            'status_label': self.get_status_display(),
            'owner': self.owner.username,
            'reserved_by': self.reserved_by.username if self.reserved_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
        }

    class Meta:
        ordering = ["-created_at"]