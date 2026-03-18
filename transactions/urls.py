from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register("reservations", ReservationViewSet, basename="reservation")
router.register("borrow", BorrowViewSet, basename="borrow")

urlpatterns = [
    path("", include(router.urls)),
]
