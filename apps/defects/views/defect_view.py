from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.defects.models import Defect
from apps.defects.serializers import DefectListSerializer, DefectSerializer
from apps.users.permissions import IsAnyEmployee, IsEngineer, IsInspectorOrEngineer


class DefectViewSet(viewsets.ModelViewSet):
    queryset = Defect.objects.select_related("wagon", "inspector").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "severity", "node", "defect_type", "wagon"]
    search_fields = ["wagon__number"]
    ordering_fields = ["inspected_at", "severity", "status"]
    ordering = ["-inspected_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return DefectListSerializer
        return DefectSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsInspectorOrEngineer()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsEngineer()]
        return [IsAnyEmployee()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "retrieve":
            qs = qs.prefetch_related("measurements", "photos")
        return qs
