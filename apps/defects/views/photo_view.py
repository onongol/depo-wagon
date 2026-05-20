from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.parsers import FormParser, MultiPartParser

from apps.defects.models import DefectPhoto
from apps.defects.serializers import DefectPhotoSerializer


class DefectPhotoViewSet(viewsets.ModelViewSet):
    queryset = DefectPhoto.objects.select_related("defect").all()
    serializer_class = DefectPhotoSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["defect"]
