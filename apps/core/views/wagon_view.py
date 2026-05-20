from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.models import Wagon
from apps.core.serializers import WagonListSerializer, WagonSerializer


class WagonViewSet(viewsets.ModelViewSet):
    queryset = Wagon.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "wagon_type", "repair_type"]
    search_fields = ["number", "owner"]
    ordering_fields = ["number", "manufacture_year", "mileage_km", "next_repair_date"]
    ordering = ["number"]

    def get_serializer_class(self):
        if self.action == "list":
            return WagonListSerializer
        return WagonSerializer
