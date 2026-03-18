
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.utils import timezone
from material_mgt.models import *
from user_mgt.models import Staff
from .serializers import *
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
            member = getattr(user, "member", None)
            if not member:
                return Reservation.objects.none()
            return Reservation.objects.filter(member_id=member)
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
    # permission_classes = [IsStackStaffForWrite]

    def perform_create(self, serializer):
        serializer.save()
