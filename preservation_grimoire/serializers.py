"""Serializer DRF modul Preservation Grimoire & Smell Test untuk aplikasi Flutter.

Diisi oleh: Syarif. Acuan: Tutorial 07, bagian "Implementasi Serializer".

Bentuk field ikuti PreservationGuide.to_dict() yang dipakai endpoint /json/ lama, supaya model Dart
di Flutter sama dengan data situs web. Field hasil hitungan (label, status, dsb.) dibuat
read-only lewat SerializerMethodField atau read_only_fields.
"""
from rest_framework import serializers  # noqa: F401

from preservation_grimoire.models import PreservationGuide  # noqa: F401

# TODO (Checkpoint 1): class PreservationGuideSerializer(serializers.ModelSerializer): ...
