
from rest_framework.viewsets import ModelViewSet
from material_mgt.models import *
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

    def get_queryset(self):
        user = self.request.user
        if _norm_role(getattr(user, "role", None)) == "MEMBER":
            member = getattr(user, "member", None)
            if not member:
                return Reservation.objects.none()
            return Reservation.objects.filter(member_id=member)
        return Reservation.objects.all()

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()
