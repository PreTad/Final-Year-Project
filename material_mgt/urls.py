from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DigitalMaterialViewSet,
    GenerateMaterialDescriptionAPIView,
    PhysicalMaterialViewSet,
)

router = DefaultRouter()
router.register("physical-materials", PhysicalMaterialViewSet, basename="physical-material")
router.register("digital-materials", DigitalMaterialViewSet, basename="digital-material")

urlpatterns = [
    path("generate-description/", GenerateMaterialDescriptionAPIView.as_view(), name="generate-material-description"),
    path("", include(router.urls)),
]