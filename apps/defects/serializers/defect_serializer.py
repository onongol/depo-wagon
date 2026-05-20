from rest_framework import serializers

from apps.defects.models import Defect
from apps.defects.serializers.measurement_serializer import DefectMeasurementSerializer
from apps.defects.serializers.photo_serializer import DefectPhotoSerializer


class DefectListSerializer(serializers.ModelSerializer):
    node_display = serializers.CharField(source="get_node_display", read_only=True)
    defect_display = serializers.CharField(source="get_defect_display", read_only=True)
    severity_display = serializers.CharField(
        source="get_severity_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    wagon_number = serializers.CharField(source="wagon.number", read_only=True)

    class Meta:
        model = Defect
        fields = [
            "id",
            "wagon",
            "wagon_number",
            "node",
            "node_display",
            "defect",
            "defect_display",
            "severity",
            "severity_display",
            "status",
            "status_display",
            "inspected_at",
        ]


class DefectSerializer(serializers.ModelSerializer):
    node_display = serializers.CharField(source="get_node_display", read_only=True)
    defect_display = serializers.CharField(source="get_defect_display", read_only=True)
    severity_display = serializers.CharField(
        source="get_severity_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    verdict_display = serializers.CharField(
        source="get_verdict_display", read_only=True
    )
    ai_verdict_display = serializers.CharField(
        source="get_ai_verdict_display", read_only=True
    )
    is_repaired = serializers.BooleanField(read_only=True)
    measurements = DefectMeasurementSerializer(many=True, read_only=True)
    photos = DefectPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Defect
        fields = [
            "id",
            "wagon",
            "node",
            "node_display",
            "defect",
            "defect_display",
            "severity",
            "severity_display",
            "status",
            "status_display",
            "description",
            "ai_defect_class",
            "ai_confidence",
            "ai_recommendation",
            "ai_verdict",
            "ai_verdict_display",
            "verdict",
            "verdict_display",
            "is_repaired",
            "inspector",
            "repaired_at",
            "inspected_at",
            "created_at",
            "updated_at",
            "measurements",
            "photos",
        ]
        read_only_fields = ["created_at", "updated_at"]
