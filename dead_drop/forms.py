from django import forms
from django.utils import timezone

from .models import FoodListing

class FoodListingForm(forms.ModelForm):
    class Meta:
        model = FoodListing
        fields = (
            "food_name",
            "description",
            "pickup_location",
            "pickup_time",
            "pickup_notes",
            "latitude",
            "longitude",
        )
        widgets = {
            "pickup_time": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def clean_pickup_time(self):
        pickup_time = self.cleaned_data["pickup_time"]
        if pickup_time <= timezone.now():
            raise forms.ValidationError("Jadwal penjemputan harus di waktu mendatang.")
        return pickup_time