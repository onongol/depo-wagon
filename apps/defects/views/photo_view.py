from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.parsers import FormParser, MultiPartParser

from apps.defects.models import DefectPhoto
from apps.defects.serializers import DefectPhotoSerializer
from apps.users.permissions import (
    IsAnyEmployee,
    IsEngineerOrManager,
    IsInspectorEngineerOrManager,
)


class DefectPhotoViewSet(viewsets.ModelViewSet):
    queryset = DefectPhoto.objects.select_related(
        "defect__wagon", "defect__inspector"
    ).all()
    serializer_class = DefectPhotoSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["defect"]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [IsInspectorEngineerOrManager()]
        if self.action == "destroy":
            return [IsEngineerOrManager()]
        return [IsAnyEmployee()]
