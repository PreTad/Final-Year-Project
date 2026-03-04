from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DigitalMaterialViewSet,
    PhysicalMaterialViewSet,
)

router = DefaultRouter()
router.register("physical-materials", PhysicalMaterialViewSet, basename="physical-material")
router.register("digital-materials", DigitalMaterialViewSet, basename="digital-material")

urlpatterns = [
    path("", include(router.urls)),
]
