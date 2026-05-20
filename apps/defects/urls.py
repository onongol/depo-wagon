from rest_framework.routers import DefaultRouter

from apps.defects.views import (
    DefectMeasurementViewSet,
    DefectPhotoViewSet,
    DefectViewSet,
)

router = DefaultRouter()
router.register(r"defects", DefectViewSet, basename="defect")
router.register(r"measurements", DefectMeasurementViewSet, basename="measurement")
router.register(r"photos", DefectPhotoViewSet, basename="photo")

urlpatterns = router.urls
