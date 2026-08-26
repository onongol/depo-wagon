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

    def update(self, instance, validated_data):
        """Keep a measurement on the defect it was recorded against.

        `defect` has to stay writable so create can set it, so reassignment
        is refused here rather than through read_only_fields.
        """
        validated_data.pop("defect", None)
        return super().update(instance, validated_data)
