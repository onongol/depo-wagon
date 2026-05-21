from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.parsers import FormParser, MultiPartParser

from apps.defects.models import DefectPhoto
from apps.defects.serializers import DefectPhotoSerializer
from apps.users.permissions import IsAnyEmployee, IsEngineer, IsInspectorOrEngineer


class DefectPhotoViewSet(viewsets.ModelViewSet):
    queryset = DefectPhoto.objects.select_related("defect").all()
    serializer_class = DefectPhotoSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["defect"]

    def get_permissions(self):
        if self.action == "create":
            return [IsInspectorOrEngineer()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsEngineer()]
        return [IsAnyEmployee()]
