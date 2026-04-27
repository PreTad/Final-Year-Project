from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DigitalMaterialViewSet,
    GenerateMaterialDescriptionAPIView,
    MaterialBookmarkViewSet,
    MaterialFavoriteViewSet,
    MaterialFeedbackViewSet,
    MaterialInteractionStatsAPIView,
    PhysicalMaterialViewSet,
)

router = DefaultRouter()
router.register("physical-materials", PhysicalMaterialViewSet, basename="physical-material")
router.register("digital-materials", DigitalMaterialViewSet, basename="digital-material")
router.register("feedback", MaterialFeedbackViewSet, basename="material-feedback")
router.register("favorites", MaterialFavoriteViewSet, basename="material-favorite")
router.register("bookmarks", MaterialBookmarkViewSet, basename="material-bookmark")

urlpatterns = [
    path("generate-description/", GenerateMaterialDescriptionAPIView.as_view(), name="generate-material-description"),
    path("interactions/stats/", MaterialInteractionStatsAPIView.as_view(), name="material-interaction-stats"),
    path("", include(router.urls)),
]
