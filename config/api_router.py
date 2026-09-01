from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from apps.core.views import EmployeeViewSet, WagonViewSet
from apps.defects.views import (
    DefectMeasurementViewSet,
    DefectPhotoViewSet,
    DefectViewSet,
)
from apps.users.views_user import UserViewSet

# Browsable api-root is a development aid; production gets no root view.
router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register(r"wagons", WagonViewSet, basename="wagon")
router.register(r"employees", EmployeeViewSet, basename="employee")
router.register(r"defects", DefectViewSet, basename="defect")
router.register(r"measurements", DefectMeasurementViewSet, basename="measurement")
router.register(r"photos", DefectPhotoViewSet, basename="photo")
router.register(r"users", UserViewSet, basename="user")

urlpatterns = router.urls
