"""Serializer DRF modul Pantry Death Clock untuk aplikasi Flutter.

Diisi oleh: Michael Evan. Acuan: Tutorial 07, bagian "Implementasi Serializer".

Bentuk field ikuti PantryItem.to_dict() yang dipakai endpoint /json/ lama, supaya model Dart
di Flutter sama dengan data situs web. Field hasil hitungan (label, status, dsb.) dibuat
read-only lewat SerializerMethodField atau read_only_fields.
"""
from rest_framework import serializers  # noqa: F401

from death_clock.models import PantryItem  # noqa: F401

# TODO (Checkpoint 1): class PantryItemSerializer(serializers.ModelSerializer): ...
