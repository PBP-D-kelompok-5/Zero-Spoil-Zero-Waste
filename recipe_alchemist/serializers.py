"""Serializer DRF modul Recipe Alchemist untuk aplikasi Flutter.

Diisi oleh: Nuno. Acuan: Tutorial 07, bagian "Implementasi Serializer".

Bentuk field ikuti Recipe.to_dict() yang dipakai endpoint /json/ lama, supaya model Dart
di Flutter sama dengan data situs web. Field hasil hitungan (label, status, dsb.) dibuat
read-only lewat SerializerMethodField atau read_only_fields.
"""
from rest_framework import serializers  # noqa: F401

from recipe_alchemist.models import Recipe  # noqa: F401

# TODO (Checkpoint 1): class RecipeSerializer(serializers.ModelSerializer): ...
