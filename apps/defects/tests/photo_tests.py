import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.defects.models import DefectPhoto


def make_image(name="test.jpg"):
    return SimpleUploadedFile(name, b"\x00" * 8, content_type="image/jpeg")


@pytest.mark.django_db
class TestDefectPhotoModel:
    def test_create_photo(self, defect):
        photo = DefectPhoto.objects.create(defect=defect, image=make_image())
        assert photo.pk is not None

    def test_str_contains_date(self, defect):
        photo = DefectPhoto.objects.create(defect=defect, image=make_image())
        assert str(photo.uploaded_at.year) in str(photo)

    def test_uploaded_at_set_automatically(self, defect):
        photo = DefectPhoto.objects.create(defect=defect, image=make_image())
        assert photo.uploaded_at is not None

    def test_defect_deleted_cascades_photo(self, defect):
        photo = DefectPhoto.objects.create(defect=defect, image=make_image())
        pk = photo.pk
        defect.delete()
        assert not DefectPhoto.objects.filter(pk=pk).exists()

    def test_multiple_photos_per_defect(self, defect):
        for i in range(3):
            DefectPhoto.objects.create(
                defect=defect, image=make_image(f"photo_{i}.jpg")
            )
        assert defect.photos.count() == 3
