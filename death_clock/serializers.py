"""Serializer DRF modul Pantry Death Clock untuk aplikasi Flutter.

Field-nya sama dengan PantryItem.to_dict() yang dipakai endpoint /json/ lama, supaya model
Dart di Flutter sama dengan data situs web. Status, sisa hari, persentase umur, dan label
hitung mundur dihitung dari tanggal saat dibaca (property di model), jadi semuanya read-only.
"""
from rest_framework import serializers

from death_clock.models import PantryItem


class PantryItemSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    unit_label = serializers.CharField(source='get_unit_display', read_only=True)
    storage_label = serializers.CharField(source='get_storage_display', read_only=True)
    days_left = serializers.IntegerField(read_only=True)
    countdown_label = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    status_label = serializers.CharField(read_only=True)
    life_percent = serializers.IntegerField(read_only=True)
    is_resurrected = serializers.BooleanField(read_only=True)

    class Meta:
        model = PantryItem
        fields = [
            'id', 'name',
            'category', 'category_label',
            'quantity', 'unit', 'unit_label',
            'storage', 'storage_label',
            'purchase_date', 'expiry_date', 'expiry_is_estimate',
            'days_left', 'countdown_label', 'status', 'status_label', 'life_percent',
            'notes', 'is_resurrected', 'resurrected_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['expiry_is_estimate', 'resurrected_at', 'created_at', 'updated_at']
