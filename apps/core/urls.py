from rest_framework.routers import DefaultRouter

from apps.core.views import EmployeeViewSet, WagonViewSet

router = DefaultRouter()
router.register(r"wagons", WagonViewSet, basename="wagon")
router.register(r"employees", EmployeeViewSet, basename="employee")

urlpatterns = router.urls
