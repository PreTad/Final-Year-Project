from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register("reservations", ReservationViewSet, basename="reservation")
router.register("borrow", BorrowViewSet, basename="borrow")
router.register("return", ReturnViewSet, basename="return")
router.register("policy-config", PolicyConfigurationViewSet, basename="policy-config")
# router.register("borrow/my", Borro, basename="borrow-my")

urlpatterns = [
    path("", include(router.urls)),
]
