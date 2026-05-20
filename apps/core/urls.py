from rest_framework.routers import DefaultRouter

from apps.core.views import WagonViewSet

router = DefaultRouter()
router.register(r"wagons", WagonViewSet, basename="wagon")

urlpatterns = router.urls
