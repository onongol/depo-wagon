from datetime import datetime, timezone

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from apps.core.constants import Department
from apps.defects.constants import DefectNode, DefectSeverity, DefectStatus, DefectType
from apps.defects.models import Defect


@pytest.fixture
def defect_data(wagon):
    return {
        "wagon": wagon.pk,
        "node": DefectNode.BODY,
        "defect_type": DefectType.CRACK,
        "severity": DefectSeverity.MEDIUM,
        "inspected_at": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc).isoformat(),
    }


@pytest.mark.django_db
class TestDefectList:
    def test_list_returns_200(self, api_client):
        response = api_client.get(reverse("defect-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_list_returns_all_defects(self, api_client, wagon, employee):
        baker.make("defects.Defect", wagon=wagon, inspector=employee, _quantity=3)
        response = api_client.get(reverse("defect-list"))
        assert response.data["count"] == 3

    def test_list_uses_list_serializer(self, api_client, defect):
        response = api_client.get(reverse("defect-list"))
        result = next(r for r in response.data["results"] if r["id"] == str(defect.pk))
        assert "measurements" not in result
        assert "photos" not in result
        assert "description" not in result
        assert "wagon_number" in result
        assert "node_display" in result
        assert "severity_display" in result
        assert "status_display" in result


@pytest.mark.django_db
class TestDefectRetrieve:
    def test_retrieve_returns_200(self, api_client, defect):
        response = api_client.get(reverse("defect-detail", args=[defect.pk]))
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_not_found_returns_404(self, api_client):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = api_client.get(reverse("defect-detail", args=[fake_uuid]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_uses_full_serializer(self, api_client, defect):
        response = api_client.get(reverse("defect-detail", args=[defect.pk]))
        assert "measurements" in response.data
        assert "photos" in response.data
        assert "description" in response.data
        assert "ai_confidence" in response.data

    def test_retrieve_includes_nested_measurements(self, api_client, defect):
        baker.make("defects.DefectMeasurement", defect=defect, _quantity=2)
        response = api_client.get(reverse("defect-detail", args=[defect.pk]))
        assert len(response.data["measurements"]) == 2

    def test_retrieve_includes_nested_photos(self, api_client, defect):
        baker.make("defects.DefectPhoto", defect=defect, _quantity=2)
        response = api_client.get(reverse("defect-detail", args=[defect.pk]))
        assert len(response.data["photos"]) == 2


@pytest.mark.django_db
class TestDefectCreate:
    def test_create_returns_201(self, api_client, defect_data):
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_saves_to_db(self, api_client, defect_data, wagon):
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Defect.objects.filter(wagon=wagon, node=DefectNode.BODY).exists()

    def test_create_default_status_is_open(self, api_client, defect_data):
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        defect = Defect.objects.get(pk=response.data["id"])
        assert defect.status == DefectStatus.OPEN


@pytest.mark.django_db
class TestDefectUpdate:
    def test_patch_returns_200(self, api_client, defect):
        response = api_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"status": DefectStatus.IN_PROGRESS},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_patch_updates_field(self, api_client, defect):
        response = api_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"status": DefectStatus.CLOSED},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        defect.refresh_from_db()
        assert defect.status == DefectStatus.CLOSED


@pytest.mark.django_db
class TestDefectDelete:
    def test_delete_returns_204(self, api_client, defect):
        response = api_client.delete(reverse("defect-detail", args=[defect.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_removes_from_db(self, api_client, defect):
        pk = defect.pk
        response = api_client.delete(reverse("defect-detail", args=[pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Defect.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestDefectFilters:
    def test_filter_by_status(self, api_client, wagon, employee):
        baker.make(
            "defects.Defect",
            wagon=wagon,
            inspector=employee,
            status=DefectStatus.OPEN,
            _quantity=2,
        )
        baker.make(
            "defects.Defect",
            wagon=wagon,
            inspector=employee,
            status=DefectStatus.CLOSED,
        )
        response = api_client.get(reverse("defect-list"), {"status": DefectStatus.OPEN})
        assert response.data["count"] == 2

    def test_filter_by_severity(self, api_client, wagon, employee):
        baker.make(
            "defects.Defect",
            wagon=wagon,
            inspector=employee,
            severity=DefectSeverity.HIGH,
            _quantity=2,
        )
        baker.make(
            "defects.Defect",
            wagon=wagon,
            inspector=employee,
            severity=DefectSeverity.LOW,
        )
        response = api_client.get(
            reverse("defect-list"), {"severity": DefectSeverity.HIGH}
        )
        assert response.data["count"] == 2

    def test_filter_by_wagon(self, api_client, wagon, employee):
        other_wagon = baker.make("core.Wagon", manufacture_year=2000)
        baker.make("defects.Defect", wagon=wagon, inspector=employee, _quantity=2)
        baker.make("defects.Defect", wagon=other_wagon, inspector=employee)
        response = api_client.get(reverse("defect-list"), {"wagon": wagon.pk})
        assert response.data["count"] == 2

    def test_search_by_wagon_number(self, api_client, defect):
        response = api_client.get(
            reverse("defect-list"), {"search": defect.wagon.number}
        )
        assert response.data["count"] == 1
        result = next(r for r in response.data["results"] if r["id"] == str(defect.pk))
        assert result["wagon_number"] == defect.wagon.number


@pytest.mark.django_db
class TestDefectValidation:
    def test_create_missing_inspected_at_returns_400(self, api_client, wagon):
        data = {
            "wagon": wagon.pk,
            "node": DefectNode.BODY,
            "defect_type": DefectType.CRACK,
            "severity": DefectSeverity.MEDIUM,
        }
        response = api_client.post(reverse("defect-list"), data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "inspected_at" in response.data

    def test_create_invalid_node_returns_400(self, api_client, defect_data):
        defect_data["node"] = "invalid_node"
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "node" in response.data

    def test_create_invalid_severity_returns_400(self, api_client, defect_data):
        defect_data["severity"] = "invalid_severity"
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "severity" in response.data

    def test_patch_invalid_status_returns_400(self, api_client, defect):
        response = api_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"status": "invalid_status"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.data


@pytest.mark.django_db
class TestDefectDepartmentValidation:
    def test_valid_node_for_department_returns_201(self, api_client, defect_data):
        defect_data["department"] = Department.REPAIR_1
        defect_data["node"] = DefectNode.BODY
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_invalid_node_for_department_returns_400(self, api_client, defect_data):
        defect_data["department"] = Department.WHEELSET
        defect_data["node"] = DefectNode.BODY
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "node" in response.data

    def test_patch_invalid_node_for_department_returns_400(self, api_client, defect):
        defect.department = Department.WHEELSET
        defect.save()
        response = api_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"node": DefectNode.BODY},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "node" in response.data

    def test_no_department_skips_node_validation(self, api_client, defect_data):
        defect_data["node"] = DefectNode.BODY
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestDefectResponsibleEmployee:
    def test_human_factor_without_responsible_returns_400(
        self, api_client, defect_data
    ):
        defect_data["defect_type"] = DefectType.HUMAN_FACTOR
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "responsible_employee" in response.data

    def test_human_factor_with_responsible_returns_201(
        self, api_client, defect_data, wagon
    ):
        responsible = baker.make("core.Employee", department=Department.REPAIR_1)
        defect_data["defect_type"] = DefectType.HUMAN_FACTOR
        defect_data["department"] = Department.REPAIR_1
        defect_data["node"] = DefectNode.BODY
        defect_data["responsible_employee"] = responsible.pk
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_responsible_from_wrong_department_returns_400(
        self, api_client, defect_data
    ):
        responsible = baker.make("core.Employee", department=Department.WHEELSET)
        defect_data["department"] = Department.REPAIR_1
        defect_data["node"] = DefectNode.BODY
        defect_data["responsible_employee"] = responsible.pk
        response = api_client.post(reverse("defect-list"), defect_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "responsible_employee" in response.data

    def test_patch_add_responsible_employee(self, api_client, defect):
        defect.department = Department.REPAIR_1
        defect.node = DefectNode.BODY
        defect.save()
        responsible = baker.make("core.Employee", department=Department.REPAIR_1)
        response = api_client.patch(
            reverse("defect-detail", args=[defect.pk]),
            {"responsible_employee": responsible.pk},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        defect.refresh_from_db()
        assert defect.responsible_employee_id == responsible.pk
