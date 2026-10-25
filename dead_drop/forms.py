from django import forms
from django.utils import timezone

from dead_drop.models import FoodListing


class FoodListingForm(forms.ModelForm):
    class Meta:
        model = FoodListing
        fields =  ('food_name', 'description', 'pickup_location','pickup_time', 'pickup_notes', 'latitude', 'longitude')

    def clean_pickup_time(self):
        time = self.cleaned_data["pickup_time"]
        if time <= timezone.now():
            raise forms.ValidationError("Jadwal penjemputan harus di waktu mendatang.")
        return time