"""Serializer DRF modul Preservation Grimoire & Smell Test untuk aplikasi Flutter.

Diisi oleh: Syarif. Acuan: Tutorial 07, bagian "Implementasi Serializer".

Bentuk field ikuti PreservationGuide.to_dict() yang dipakai endpoint /json/ lama, supaya model Dart
di Flutter sama dengan data situs web. Field hasil hitungan (label, status, dsb.) dibuat
read-only lewat SerializerMethodField atau read_only_fields.
"""
from rest_framework import serializers

from preservation_grimoire.models import PreservationGuide


class PreservationGuideSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    author = serializers.CharField(source='author.username', read_only=True)
    total_upvotes = serializers.IntegerField(source='upvotes.count', read_only=True)

    class Meta:
        model = PreservationGuide
        fields = [
            'id',
            'title',
            'category',
            'category_label',
            'preservation_method',
            'content',
            'smell_indicator',
            'texture_indicator',
            'visual_indicator',
            'author',
            'total_upvotes',
            'created_at',
            'updated_at',
        ]