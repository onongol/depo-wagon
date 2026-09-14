from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from apps.defects.models import DefectMeasurement
from apps.defects.serializers import DefectMeasurementSerializer
from apps.users.permissions import (
    IsAnyEmployee,
    IsEngineerOrManager,
    IsInspectorEngineerOrManager,
)


class DefectMeasurementViewSet(viewsets.ModelViewSet):
    queryset = DefectMeasurement.objects.select_related(
        "defect__wagon", "defect__inspector"
    ).all()
    serializer_class = DefectMeasurementSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["defect", "dimension"]

    def get_permissions(self):
        if self.action == "create":
            return [IsInspectorEngineerOrManager()]
        if self.action in {"update", "partial_update", "destroy"}:
            return [IsEngineerOrManager()]
        return [IsAnyEmployee()]
