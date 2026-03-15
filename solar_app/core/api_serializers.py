"""Serializers for API request validation and response documentation."""

from rest_framework import serializers

from core.models import Equipo, SelectedEquipo


class EquipmentFilterQuerySerializer(serializers.Serializer):
    categoria_equipo = serializers.ChoiceField(
        choices=Equipo.Categoria.choices,
        required=False,
    )
    fabricante = serializers.CharField(required=False, max_length=100)
    potencia_min = serializers.FloatField(required=False, min_value=0)
    potencia_max = serializers.FloatField(required=False, min_value=0)
    en_stock = serializers.BooleanField(required=False)
    buscar = serializers.CharField(required=False, max_length=100)


class EquipmentSelectSerializer(serializers.Serializer):
    equipo_id = serializers.IntegerField(min_value=1)
    tipo_equipo = serializers.ChoiceField(choices=SelectedEquipo.TipoEquipo.choices)
    cantidad = serializers.IntegerField(required=False, min_value=1, default=1)
    notas = serializers.CharField(required=False, allow_blank=True, default="")


class EquipmentQuantityUpdateSerializer(serializers.Serializer):
    qty_change = serializers.IntegerField()

    def validate_qty_change(self, value):
        if value == 0:
            raise serializers.ValidationError("qty_change no puede ser 0")
        return value


class SuccessEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()


class ErrorEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    error = serializers.CharField()
