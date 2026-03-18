from rest_framework.generics import CreateAPIView
from rest_framework.generics import DestroyAPIView
from django.contrib.auth import update_session_auth_hash
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from material_mgt.models import *
from material_mgt.serializers import *
from user_mgt.models import Staff
from user_mgt.permissions import *
# Create your views here.

def _norm_role(role):
    return "".join(str(role or "").upper().split())


def _get_staff_profile_or_error(user):
    staff_profile = getattr(user, "staff", None)
    if staff_profile:
        return staff_profile

    if getattr(user, "member", None):
        raise ValidationError(
            {"detail": "This user still has a MEMBER profile. Convert/remove Member profile first."}
        )

    if getattr(user, "department_head", None):
        raise ValidationError(
            {"detail": "This user still has a DEPARTMENT HEAD profile. Convert/remove it first."}
        )

    staff_roles = {"STACKSTAFF", "TECHNICALSTAFF", "FRONTDESKSTAFF", "ADMIN", "SUPERADMIN"}
    if _norm_role(getattr(user, "role", None)) not in staff_roles:
        raise ValidationError({"detail": "Only staff-role users can create materials."})

    return Staff.objects.create(user_id=user)

class PhysicalMaterialViewSet(ModelViewSet):
    queryset = PhysicalMaterial.objects.all()
    serializer_class = PhysicalMaterialSerializer
    # permission_classes = [IsAuthenticated, IsTechnicalStaffForWrite]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff_profile = _get_staff_profile_or_error(request.user)

        data = serializer.validated_data
        total_copies = int(data.get("total_copies") or 0)
        if total_copies < 1:
            raise ValidationError({"total_copies": "total_copies must be at least 1."})

        available_copies = data.get("available_copies")
        if available_copies is None:
            available_copies = total_copies
        elif int(available_copies) > total_copies:
            raise ValidationError(
                {"available_copies": "available_copies cannot exceed total_copies."}
            )

        material = serializer.save(
            created_by=staff_profile,
            available_copies=available_copies,
        )
        output = self.get_serializer(material)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        serializer.save()


class DigitalMaterialViewSet(ModelViewSet):
    queryset = DigitalMaterial.objects.all()
    serializer_class = DigitalMaterialSerializer
    # permission_classes = [IsAuthenticated, IsTechnicalStaffForWrite]

    def perform_create(self, serializer):
        serializer.save(created_by=_get_staff_profile_or_error(self.request.user))

    def perform_update(self, serializer):
        serializer.save()
