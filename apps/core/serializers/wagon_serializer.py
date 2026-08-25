from django.utils import timezone
from rest_framework import serializers

from apps.core.models import Wagon


class WagonListSerializer(serializers.ModelSerializer):
    wagon_type_display = serializers.CharField(
        source="get_wagon_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    needs_repair_soon = serializers.BooleanField(read_only=True)
    manufacture_year = serializers.IntegerField(
        min_value=1900, max_value=timezone.now().year
    )

    class Meta:
        model = Wagon
        fields = [
            "id",
            "number",
            "wagon_type",
            "wagon_type_display",
            "status",
            "status_display",
            "manufacture_year",
            "next_repair_date",
            "needs_repair_soon",
        ]


class WagonSerializer(serializers.ModelSerializer):
    wagon_type_display = serializers.CharField(
        source="get_wagon_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    repair_type_display = serializers.CharField(
        source="get_repair_type_display", read_only=True
    )
    needs_repair_soon = serializers.BooleanField(read_only=True)
    manufacture_year = serializers.IntegerField(
        min_value=1900, max_value=timezone.now().year
    )

    class Meta:
        model = Wagon
        fields = [
            "id",
            "number",
            "wagon_type",
            "wagon_type_display",
            "manufacture_year",
            "last_repair_date",
            "next_repair_date",
            "needs_repair_soon",
            "mileage_km",
            "owner",
            "status",
            "status_display",
            "repair_type",
            "repair_type_display",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
