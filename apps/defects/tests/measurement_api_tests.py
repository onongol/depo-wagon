from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from apps.defects.constants import MeasurementDimension
from apps.defects.models import DefectMeasurement


@pytest.fixture
def measurement_data(defect):
    return {
        "defect": str(defect.pk),
        "dimension": MeasurementDimension.DEPTH,
        "value": "5.50",
        "unit": "mm",
    }


@pytest.mark.django_db
class TestMeasurementList:
    def test_list_returns_200(self, api_client):
        response = api_client.get(reverse("measurement-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_list_returns_all_measurements(self, api_client, defect):
        baker.make("defects.DefectMeasurement", defect=defect, _quantity=3)
        response = api_client.get(reverse("measurement-list"))
        assert response.data["count"] == 3

    def test_list_contains_expected_fields(self, api_client, defect):
        measurement = baker.make("defects.DefectMeasurement", defect=defect)
        response = api_client.get(reverse("measurement-list"))
        result = next(r for r in response.data["results"] if r["id"] == measurement.pk)
        assert "dimension_display" in result
        assert "is_exceeded" in result
        assert "value" in result
        assert "norm_value" in result


@pytest.mark.django_db
class TestMeasurementRetrieve:
    def test_retrieve_returns_200(self, api_client, defect):
        measurement = baker.make("defects.DefectMeasurement", defect=defect)
        response = api_client.get(reverse("measurement-detail", args=[measurement.pk]))
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_not_found_returns_404(self, api_client):
        response = api_client.get(reverse("measurement-detail", args=[99999]))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestMeasurementCreate:
    def test_create_returns_201(self, api_client, measurement_data):
        response = api_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_saves_to_db(self, api_client, measurement_data, defect):
        response = api_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert DefectMeasurement.objects.filter(
            defect=defect, dimension=MeasurementDimension.DEPTH
        ).exists()

    def test_create_without_norm_value(self, api_client, measurement_data):
        response = api_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["norm_value"] is None

    def test_create_missing_value_returns_400(self, api_client, measurement_data):
        del measurement_data["value"]
        response = api_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "value" in response.data

    def test_create_invalid_dimension_returns_400(self, api_client, measurement_data):
        measurement_data["dimension"] = "invalid"
        response = api_client.post(
            reverse("measurement-list"), measurement_data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "dimension" in response.data


@pytest.mark.django_db
class TestMeasurementUpdate:
    def test_patch_returns_200(self, api_client, defect):
        measurement = baker.make(
            "defects.DefectMeasurement", defect=defect, value=Decimal("5.00")
        )
        response = api_client.patch(
            reverse("measurement-detail", args=[measurement.pk]),
            {"value": "7.50"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_patch_updates_value(self, api_client, defect):
        measurement = baker.make(
            "defects.DefectMeasurement", defect=defect, value=Decimal("5.00")
        )
        response = api_client.patch(
            reverse("measurement-detail", args=[measurement.pk]),
            {"value": "7.50"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        measurement.refresh_from_db()
        assert measurement.value == Decimal("7.50")


@pytest.mark.django_db
class TestMeasurementDelete:
    def test_delete_returns_204(self, api_client, defect):
        measurement = baker.make("defects.DefectMeasurement", defect=defect)
        response = api_client.delete(
            reverse("measurement-detail", args=[measurement.pk])
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_removes_from_db(self, api_client, defect):
        measurement = baker.make("defects.DefectMeasurement", defect=defect)
        pk = measurement.pk
        response = api_client.delete(reverse("measurement-detail", args=[pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DefectMeasurement.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestMeasurementFilters:
    def test_filter_by_defect(self, api_client, wagon, employee):
        defect_a = baker.make("defects.Defect", wagon=wagon, inspector=employee)
        defect_b = baker.make("defects.Defect", wagon=wagon, inspector=employee)
        baker.make("defects.DefectMeasurement", defect=defect_a, _quantity=2)
        baker.make("defects.DefectMeasurement", defect=defect_b)
        response = api_client.get(
            reverse("measurement-list"), {"defect": str(defect_a.pk)}
        )
        assert response.data["count"] == 2

    def test_filter_by_dimension(self, api_client, defect):
        baker.make(
            "defects.DefectMeasurement",
            defect=defect,
            dimension=MeasurementDimension.DEPTH,
            _quantity=2,
        )
        baker.make(
            "defects.DefectMeasurement",
            defect=defect,
            dimension=MeasurementDimension.WIDTH,
        )
        response = api_client.get(
            reverse("measurement-list"), {"dimension": MeasurementDimension.DEPTH}
        )
        assert response.data["count"] == 2


@pytest.mark.django_db
class TestMeasurementIsExceeded:
    def test_is_exceeded_false_when_no_norm(self, api_client, defect):
        measurement = baker.make(
            "defects.DefectMeasurement",
            defect=defect,
            value=Decimal("10.00"),
            norm_value=None,
        )
        response = api_client.get(reverse("measurement-detail", args=[measurement.pk]))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_exceeded"] is False

    def test_is_exceeded_false_when_below_norm(self, api_client, defect):
        measurement = baker.make(
            "defects.DefectMeasurement",
            defect=defect,
            value=Decimal("5.00"),
            norm_value=Decimal("10.00"),
        )
        response = api_client.get(reverse("measurement-detail", args=[measurement.pk]))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_exceeded"] is False

    def test_is_exceeded_true_when_above_norm(self, api_client, defect):
        measurement = baker.make(
            "defects.DefectMeasurement",
            defect=defect,
            value=Decimal("15.00"),
            norm_value=Decimal("10.00"),
        )
        response = api_client.get(reverse("measurement-detail", args=[measurement.pk]))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_exceeded"] is True
