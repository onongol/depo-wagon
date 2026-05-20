from rest_framework import serializers

from apps.defects.models import DefectMeasurement


class DefectMeasurementSerializer(serializers.ModelSerializer):
    dimension_display = serializers.CharField(
        source="get_dimension_display", read_only=True
    )
    is_exceeded = serializers.BooleanField(read_only=True)

    class Meta:
        model = DefectMeasurement
        fields = [
            "id",
            "defect",
            "dimension",
            "dimension_display",
            "value",
            "norm_value",
            "unit",
            "is_exceeded",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
