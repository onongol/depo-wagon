from rest_framework import serializers

from apps.defects.models import DefectPhoto


class DefectPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefectPhoto
        fields = ["id", "defect", "image", "uploaded_at"]
        read_only_fields = ["uploaded_at"]
