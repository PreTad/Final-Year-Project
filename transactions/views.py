
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework import status
from django.utils import timezone
from material_mgt.models import *
from user_mgt.models import Staff
from .serializers import *
from .services import sync_overdue_borrow_statuses
from user_mgt.permissions import *
# Create your views here.

def _norm_role(role):
    return "".join(str(role or "").upper().split())


def _get_staff_profile_or_error(user):
    staff_profile = getattr(user, "staff", None)
    if staff_profile:
        return staff_profile
    return Staff.objects.create(user_id=user)

class ReservationViewSet(ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    # permission_classes = [IsAuthenticated]

    def _expire_overdue(self, qs):
        now = timezone.now()
        qs.filter(status="RESERVED", expiry_date__lt=now).update(status="EXPIRED")
        return qs

    def get_queryset(self):
        user = self.request.user
        base_qs = Reservation.objects.all()
        self._expire_overdue(base_qs)
        if _norm_role(getattr(user, "role", None)) == "MEMBER":
            return Reservation.objects.filter(member=user)
        return base_qs

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        reservation = self.get_object()
        if reservation.status != "CANCELLED":
            reservation.status = "CANCELLED"
            reservation.save(update_fields=["status"])
        return Response(status=204)
class BorrowViewSet(ModelViewSet):
    
    queryset = Borrow.objects.all().order_by("-borrow_date")
    serializer_class = BorrowSerializer
    permission_classes = [IsStackStaffForWrite]

    def get_queryset(self):
        sync_overdue_borrow_statuses()
        queryset = Borrow.objects.select_related("member", "material", "created_by").all().order_by("-borrow_date")
        user = self.request.user
        if _norm_role(getattr(user, "role", None)) == "MEMBER":
            return queryset.filter(member=user)
        return queryset

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        sync_overdue_borrow_statuses()
        user = request.user
        if not user or not user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        queryset = Borrow.objects.select_related("member", "material", "created_by").filter(member=user).order_by("-borrow_date")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReturnViewSet(ModelViewSet):

    queryset = Return.objects.all().order_by("-return_date")
    serializer_class = ReturnSerializer
    # permission_classes = [IsStackStaffForWrite]

    def get_queryset(self):
        user = self.request.user
        base_qs = Return.objects.all().order_by("-return_date")
        if _norm_role(getattr(user, "role", None)) == "MEMBER":
            return base_qs.filter(borrow__member=user)
        return base_qs

    def perform_create(self, serializer):
        serializer.save()
