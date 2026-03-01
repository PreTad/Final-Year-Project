from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter

from .views import (
    DigitalMaterialViewSet,
    LibraryViewSet,
    ChangePasswordAPIView,
    PhysicalMaterialViewSet,
    ReservationViewSet,
    UserMeAPIView,
    UserCreateAPIView,
    UserDeleteAPIView,
)

router = DefaultRouter()
router.register("libraries", LibraryViewSet, basename="library")
router.register("physical-materials", PhysicalMaterialViewSet, basename="physical-material")
router.register("digital-materials", DigitalMaterialViewSet, basename="digital-material")
router.register("reservations", ReservationViewSet, basename="reservation")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/users/create/", UserCreateAPIView.as_view(), name="user-create"),
    path("api/users/<uuid:pk>/delete/", UserDeleteAPIView.as_view(), name="user-delete"),
    path("api/auth/password/", ChangePasswordAPIView.as_view(), name="auth-change-password"),
    path("api/auth/me/", UserMeAPIView.as_view(), name="auth-me"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
