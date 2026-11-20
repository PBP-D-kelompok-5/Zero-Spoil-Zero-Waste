"""Serializer DRF modul The Dead Drop untuk aplikasi Flutter.

Diisi oleh: Joshua. Acuan: Tutorial 07, bagian "Implementasi Serializer".

Bentuk field ikuti FoodListing.to_dict() yang dipakai endpoint /json/ lama, supaya model Dart
di Flutter sama dengan data situs web. Field hasil hitungan (label, status, dsb.) dibuat
read-only lewat SerializerMethodField atau read_only_fields.
"""
from rest_framework import serializers

from dead_drop.models import FoodListing


class FoodListingSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    owner = serializers.CharField(source="owner.username", read_only=True)
    reserved_by = serializers.CharField(
        source="reserved_by.username", read_only=True, allow_null=True
    )
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)

    class Meta:
        model = FoodListing
        fields = [
            "id",
            "food_name",
            "description",
            "pickup_location",
            "pickup_time",
            "pickup_notes",
            "latitude",
            "longitude",
            "status",
            "status_label",
            "owner",
            "reserved_by",
            "created_at",
            "updated_at",
            "claimed_at",
        ]
        read_only_fields = fields
