import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from apps.core.constants import WagonStatus, WagonType
from apps.core.models import Wagon


@pytest.fixture
def wagon_data():
    return {
        "number": "87654321",
        "wagon_type": WagonType.GONDOLA_CAR,
        "manufacture_year": 2010,
        "status": WagonStatus.ACTIVE,
    }


@pytest.mark.django_db
class TestWagonList:
    def test_list_returns_200(self, api_client):
        response = api_client.get(reverse("wagon-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_list_returns_all_wagons(self, api_client):
        baker.make("core.Wagon", manufacture_year=2000, _quantity=3)
        response = api_client.get(reverse("wagon-list"))
        assert response.data["count"] == 3

    def test_list_uses_list_serializer(self, api_client, wagon):
        response = api_client.get(reverse("wagon-list"))
        result = next(
            r for r in response.data["results"] if r["number"] == wagon.number
        )
        assert "notes" not in result
        assert "mileage_km" not in result
        assert "wagon_type_display" in result
        assert "status_display" in result
        assert "needs_repair_soon" in result


@pytest.mark.django_db
class TestWagonRetrieve:
    def test_retrieve_returns_200(self, api_client, wagon):
        response = api_client.get(reverse("wagon-detail", args=[wagon.pk]))
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_not_found_returns_404(self, api_client):
        response = api_client.get(reverse("wagon-detail", args=[99999]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_uses_full_serializer(self, api_client, wagon):
        response = api_client.get(reverse("wagon-detail", args=[wagon.pk]))
        assert "notes" in response.data
        assert "mileage_km" in response.data
        assert "repair_type_display" in response.data


@pytest.mark.django_db
class TestWagonCreate:
    def test_create_returns_201(self, api_client, wagon_data):
        response = api_client.post(reverse("wagon-list"), wagon_data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_saves_to_db(self, api_client, wagon_data):
        response = api_client.post(reverse("wagon-list"), wagon_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Wagon.objects.filter(number="87654321").exists()

    def test_create_duplicate_number_returns_400(self, api_client, wagon, wagon_data):
        wagon_data["number"] = wagon.number
        response = api_client.post(reverse("wagon-list"), wagon_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestWagonUpdate:
    def test_patch_returns_200(self, api_client, wagon):
        response = api_client.patch(
            reverse("wagon-detail", args=[wagon.pk]),
            {"status": WagonStatus.REPAIR},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_patch_updates_field(self, api_client, wagon):
        api_client.patch(
            reverse("wagon-detail", args=[wagon.pk]),
            {"status": WagonStatus.REPAIR},
            format="json",
        )
        wagon.refresh_from_db()
        assert wagon.status == WagonStatus.REPAIR


@pytest.mark.django_db
class TestWagonDelete:
    def test_delete_returns_204(self, api_client, wagon):
        response = api_client.delete(reverse("wagon-detail", args=[wagon.pk]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_removes_from_db(self, api_client, wagon):
        pk = wagon.pk
        api_client.delete(reverse("wagon-detail", args=[pk]))
        assert not Wagon.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestWagonFilters:
    def test_filter_by_status(self, api_client):
        baker.make(
            "core.Wagon", manufacture_year=2000, status=WagonStatus.ACTIVE, _quantity=2
        )
        baker.make("core.Wagon", manufacture_year=2000, status=WagonStatus.REPAIR)
        response = api_client.get(reverse("wagon-list"), {"status": WagonStatus.ACTIVE})
        assert response.data["count"] == 2

    def test_search_by_number(self, api_client, wagon):
        response = api_client.get(reverse("wagon-list"), {"search": wagon.number})
        assert response.data["count"] == 1
        assert response.data["results"][0]["number"] == wagon.number

    def test_ordering_by_number(self, api_client):
        baker.make("core.Wagon", manufacture_year=2000, number="20000001")
        baker.make("core.Wagon", manufacture_year=2000, number="10000001")
        response = api_client.get(reverse("wagon-list"), {"ordering": "number"})
        numbers = [w["number"] for w in response.data["results"]]
        assert numbers == sorted(numbers)
