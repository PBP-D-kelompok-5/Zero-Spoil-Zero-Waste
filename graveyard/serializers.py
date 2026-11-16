"""Serializer DRF modul The Graveyard & Waste Analytics untuk aplikasi Flutter.

Diisi oleh: Adam. Acuan: Tutorial 07, bagian "Implementasi Serializer".

Bentuk field ikuti GraveyardItem.to_dict() yang dipakai endpoint /json/ lama, supaya model Dart
di Flutter sama dengan data situs web. Field hasil hitungan (label, status, dsb.) dibuat
read-only lewat SerializerMethodField atau read_only_fields.
"""
from rest_framework import serializers  # noqa: F401

from graveyard.models import GraveyardItem  # noqa: F401

# TODO (Checkpoint 1): class GraveyardItemSerializer(serializers.ModelSerializer): ...
