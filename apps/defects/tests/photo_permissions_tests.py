import io

import pytest
from django.urls import reverse
from model_bakery import baker
from PIL import Image
from rest_framework import status


def make_image_file(name="test.png"):
    buf = io.BytesIO()
    Image.new("RGB", (1, 1)).save(buf, format="PNG")
    buf.seek(0)
    buf.name = name
    return buf


@pytest.fixture
def photo(db, defect):
    return baker.make("defects.DefectPhoto", defect=defect)


@pytest.mark.django_db
class TestPhotoListPermissions:
    def test_anon_cannot_list(self, anon_client):
        response = anon_client.get(reverse("photo-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_can_list(self, inspector_client):
        response = inspector_client.get(reverse("photo-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_master_can_list(self, master_client):
        response = master_client.get(reverse("photo-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_engineer_can_list(self, engineer_client):
        response = engineer_client.get(reverse("photo-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_manager_can_list(self, manager_client):
        response = manager_client.get(reverse("photo-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_list(self, superuser_client):
        response = superuser_client.get(reverse("photo-list"))
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPhotoCreatePermissions:
    def test_anon_cannot_create(self, anon_client, defect):
        response = anon_client.post(
            reverse("photo-list"),
            {"defect": str(defect.pk), "image": make_image_file()},
            format="multipart",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_master_cannot_create(self, master_client, defect):
        response = master_client.post(
            reverse("photo-list"),
            {"defect": str(defect.pk), "image": make_image_file()},
            format="multipart",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_create(self, manager_client, defect):
        response = manager_client.post(
            reverse("photo-list"),
            {"defect": str(defect.pk), "image": make_image_file()},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_inspector_can_create_on_their_own_defect(self, inspector_client, wagon):
        own = baker.make(
            "defects.Defect", wagon=wagon, inspector=inspector_client.employee
        )
        response = inspector_client.post(
            reverse("photo-list"),
            {"defect": str(own.pk), "image": make_image_file()},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_inspector_cannot_create_on_another_inspectors_defect(
        self, inspector_client, defect
    ):
        response = inspector_client.post(
            reverse("photo-list"),
            {"defect": str(defect.pk), "image": make_image_file()},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "defect" in response.data

    def test_engineer_can_create(self, engineer_client, defect):
        response = engineer_client.post(
            reverse("photo-list"),
            {"defect": str(defect.pk), "image": make_image_file()},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_superuser_can_create(self, superuser_client, defect):
        response = superuser_client.post(
            reverse("photo-list"),
            {"defect": str(defect.pk), "image": make_image_file()},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestPhotoUpdateNotAllowed:
    def test_patch_not_allowed(self, api_client, photo):
        response = api_client.patch(
            reverse("photo-detail", args=[photo.pk]),
            {"image": make_image_file("updated.png")},
            format="multipart",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestPhotoDeletePermissions:
    def test_anon_cannot_delete(self, anon_client, photo):
        response = anon_client.delete(reverse("photo-detail", args=[photo.pk]))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inspector_cannot_delete(self, inspector_client, photo):
        response = inspector_client.delete(reverse("photo-detail", args=[photo.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_master_cannot_delete(self, master_client, photo):
        response = master_client.delete(reverse("photo-detail", args=[photo.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_delete(self, manager_client, photo):
        response = manager_client.delete(reverse("photo-detail", args=[photo.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_engineer_can_delete(self, engineer_client, photo):
        response = engineer_client.delete(reverse("photo-detail", args=[photo.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_superuser_can_delete(self, superuser_client, defect):
        photo2 = baker.make("defects.DefectPhoto", defect=defect)
        response = superuser_client.delete(reverse("photo-detail", args=[photo2.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestPhotoNoEmployeePermissions:
    def test_cannot_list(self, no_employee_client):
        response = no_employee_client.get(reverse("photo-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_create(self, no_employee_client, defect):
        response = no_employee_client.post(
            reverse("photo-list"),
            {"defect": str(defect.pk), "image": make_image_file()},
            format="multipart",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_update(self, no_employee_client, photo):
        response = no_employee_client.patch(
            reverse("photo-detail", args=[photo.pk]),
            {"image": make_image_file("updated.png")},
            format="multipart",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_delete(self, no_employee_client, photo):
        response = no_employee_client.delete(reverse("photo-detail", args=[photo.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN
