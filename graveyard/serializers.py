"""Serializer DRF modul The Graveyard & Waste Analytics untuk aplikasi Flutter.

Diisi oleh: Adam. Acuan: Tutorial 07, bagian "Implementasi Serializer".

Bentuk field mengikuti GraveyardItem.to_dict() yang dipakai endpoint /json/ lama, supaya model
Dart di Flutter sama dengan data situs web. Field hasil hitungan (label, estimasi berat efektif,
jejak karbon, timestamp) dibuat read-only lewat SerializerMethodField atau read_only_fields.
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from graveyard.models import GraveyardItem


class GraveyardItemSerializer(serializers.ModelSerializer):
    """Serializer untuk model GraveyardItem yang selaras dengan payload to_dict()."""

    category_label = serializers.CharField(source='get_category_display', read_only=True)
    reason_label = serializers.CharField(source='get_reason_display', read_only=True)
    unit_label = serializers.CharField(source='get_unit_display', read_only=True)
    weight_g = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.00'),
        coerce_to_string=False,
        required=False,
    )
    effective_weight_kg = serializers.SerializerMethodField()
    estimated_loss = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.00'),
        coerce_to_string=False,
        required=False,
    )
    estimated_carbon_kg = serializers.SerializerMethodField()

    class Meta:
        model = GraveyardItem
        fields = [
            'id',
            'name',
            'category',
            'category_label',
            'reason',
            'reason_label',
            'notes',
            'expiry_date',
            'disposed_at',
            'quantity',
            'unit',
            'unit_label',
            'weight_g',
            'effective_weight_kg',
            'estimated_loss',
            'estimated_carbon_kg',
            'created_at',
            'updated_at',
        ]
        read_only_fields = (
            'id',
            'category_label',
            'reason_label',
            'unit_label',
            'effective_weight_kg',
            'estimated_carbon_kg',
            'created_at',
            'updated_at',
        )

    def get_effective_weight_kg(self, obj):
        return float(obj.effective_weight_kg)

    def get_estimated_carbon_kg(self, obj):
        return float(obj.estimated_carbon_kg)

    def validate_disposed_at(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError('Tanggal dibuang tidak boleh di masa depan.')
        return value
