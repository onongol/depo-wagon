import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from model_bakery import baker
from PIL import Image
from rest_framework import status

from apps.defects.models import DefectPhoto


def make_image(name="test.png"):
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="red").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/png")


@pytest.mark.django_db
class TestPhotoList:
    def test_list_returns_200(self, api_client):
        response = api_client.get(reverse("photo-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_list_returns_all_photos(self, api_client, defect):
        baker.make("defects.DefectPhoto", defect=defect, _quantity=3)
        response = api_client.get(reverse("photo-list"))
        assert response.data["count"] == 3

    def test_list_contains_expected_fields(self, api_client, defect):
        photo = baker.make("defects.DefectPhoto", defect=defect)
        response = api_client.get(reverse("photo-list"))
        result = next(r for r in response.data["results"] if r["id"] == int(photo.pk))
        assert "image" in result
        assert "uploaded_at" in result
        assert "defect" in result


@pytest.mark.django_db
class TestPhotoRetrieve:
    def test_retrieve_returns_200(self, api_client, defect):
        photo = baker.make("defects.DefectPhoto", defect=defect)
        response = api_client.get(reverse("photo-detail", args=[photo.pk]))
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_not_found_returns_404(self, api_client):
        response = api_client.get(reverse("photo-detail", args=[99999]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_uploaded_at_is_readonly(self, api_client, defect):
        photo = baker.make("defects.DefectPhoto", defect=defect)
        response = api_client.get(reverse("photo-detail", args=[photo.pk]))
        assert response.status_code == status.HTTP_200_OK
        assert "uploaded_at" in response.data


@pytest.mark.django_db
class TestPhotoCreate:
    def test_create_returns_201(self, api_client, defect):
        data = {"defect": str(defect.pk), "image": make_image()}
        response = api_client.post(reverse("photo-list"), data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_saves_to_db(self, api_client, defect):
        data = {"defect": str(defect.pk), "image": make_image()}
        response = api_client.post(reverse("photo-list"), data)
        assert response.status_code == status.HTTP_201_CREATED
        assert DefectPhoto.objects.filter(defect=defect).exists()

    def test_create_without_image_returns_400(self, api_client, defect):
        data = {"defect": str(defect.pk)}
        response = api_client.post(reverse("photo-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "image" in response.data

    def test_create_without_defect_returns_400(self, api_client):
        data = {"image": make_image()}
        response = api_client.post(reverse("photo-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "defect" in response.data

    def test_create_invalid_file_returns_400(self, api_client, defect):
        txt_file = SimpleUploadedFile(
            "file.txt", b"not an image", content_type="text/plain"
        )
        data = {"defect": str(defect.pk), "image": txt_file}
        response = api_client.post(reverse("photo-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "image" in response.data

    def test_uploaded_at_set_automatically(self, api_client, defect):
        data = {"defect": str(defect.pk), "image": make_image()}
        response = api_client.post(reverse("photo-list"), data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["uploaded_at"] is not None


@pytest.mark.django_db
class TestPhotoDelete:
    def test_delete_returns_204(self, api_client, defect):
        photo = baker.make("defects.DefectPhoto", defect=defect)
        response = api_client.delete(reverse("photo-detail", args=[photo.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_removes_from_db(self, api_client, defect):
        photo = baker.make("defects.DefectPhoto", defect=defect)
        pk = photo.pk
        response = api_client.delete(reverse("photo-detail", args=[pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DefectPhoto.objects.filter(pk=pk).exists()

    def test_retrieve_after_delete_returns_404(self, api_client, defect):
        photo = baker.make("defects.DefectPhoto", defect=defect)
        pk = photo.pk
        api_client.delete(reverse("photo-detail", args=[pk]))
        response = api_client.get(reverse("photo-detail", args=[pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestPhotoFilters:
    def test_filter_by_defect(self, api_client, wagon, employee):
        defect_a = baker.make("defects.Defect", wagon=wagon, inspector=employee)
        defect_b = baker.make("defects.Defect", wagon=wagon, inspector=employee)
        baker.make("defects.DefectPhoto", defect=defect_a, _quantity=2)
        baker.make("defects.DefectPhoto", defect=defect_b)
        response = api_client.get(reverse("photo-list"), {"defect": str(defect_a.pk)})
        assert response.data["count"] == 2
