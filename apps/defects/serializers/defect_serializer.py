from rest_framework import serializers

from apps.defects.constants import DEPARTMENT_NODES, DefectType
from apps.defects.models import Defect
from apps.defects.serializers.measurement_serializer import DefectMeasurementSerializer
from apps.defects.serializers.photo_serializer import DefectPhotoSerializer


class DefectListSerializer(serializers.ModelSerializer):
    node_display = serializers.CharField(source="get_node_display", read_only=True)
    defect_type_display = serializers.CharField(
        source="get_defect_type_display", read_only=True
    )
    severity_display = serializers.CharField(
        source="get_severity_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    department_display = serializers.CharField(
        source="get_department_display", read_only=True
    )
    wagon_number = serializers.CharField(source="wagon.number", read_only=True)

    class Meta:
        model = Defect
        fields = [
            "id",
            "wagon",
            "wagon_number",
            "department",
            "department_display",
            "node",
            "node_display",
            "part_number",
            "defect_type",
            "defect_type_display",
            "severity",
            "severity_display",
            "status",
            "status_display",
            "inspected_at",
        ]


class DefectSerializer(serializers.ModelSerializer):
    node_display = serializers.CharField(source="get_node_display", read_only=True)
    wagon_number = serializers.CharField(source="wagon.number", read_only=True)
    defect_type_display = serializers.CharField(
        source="get_defect_type_display", read_only=True
    )
    severity_display = serializers.CharField(
        source="get_severity_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    department_display = serializers.CharField(
        source="get_department_display", read_only=True
    )
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
            "wagon_number",
            "department",
            "department_display",
            "node",
            "node_display",
            "part_number",
            "defect_type",
            "defect_type_display",
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
            "responsible_employee",
            "repaired_at",
            "inspected_at",
            "created_at",
            "updated_at",
            "measurements",
            "photos",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        """Validate node/department consistency and responsible_employee for human factor."""
        department = attrs.get("department") or (
            self.instance.department if self.instance else ""
        )
        node = attrs.get("node") or (self.instance.node if self.instance else "")

        allowed_nodes = DEPARTMENT_NODES.get(department)
        if allowed_nodes and node not in allowed_nodes:
            raise serializers.ValidationError(
                {"node": f"Node '{node}' is not valid for department '{department}'."}
            )

        defect_type = attrs.get("defect_type") or (
            self.instance.defect_type if self.instance else ""
        )
        responsible = attrs.get("responsible_employee")

        if defect_type == DefectType.HUMAN_FACTOR and not responsible:
            if not (self.instance and self.instance.responsible_employee_id):
                raise serializers.ValidationError(
                    {
                        "responsible_employee": "Required when defect type is Human Factor."
                    }
                )

        if responsible and department and responsible.department != department:
            raise serializers.ValidationError(
                {
                    "responsible_employee": (
                        f"Employee must belong to department '{department}'."
                    )
                }
            )

        return attrs
