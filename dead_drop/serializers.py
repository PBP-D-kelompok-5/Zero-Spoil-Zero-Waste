"""Serializer DRF modul The Dead Drop untuk aplikasi Flutter.

Diisi oleh: Joshua. Acuan: Tutorial 07, bagian "Implementasi Serializer".

Bentuk field ikuti FoodListing.to_dict() yang dipakai endpoint /json/ lama, supaya model Dart
di Flutter sama dengan data situs web. Field hasil hitungan (label, status, dsb.) dibuat
read-only lewat SerializerMethodField atau read_only_fields.
"""
from rest_framework import serializers  # noqa: F401

from dead_drop.models import FoodListing  # noqa: F401

# TODO (Checkpoint 1): class FoodListingSerializer(serializers.ModelSerializer): ...
