from rest_framework.generics import CreateAPIView
from rest_framework.generics import DestroyAPIView
import re
from django.db import transaction
from django.contrib.auth import update_session_auth_hash
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser
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


def _copy_prefix_from_title(title):
    letters_only = "".join(ch for ch in (title or "").upper() if ch.isalpha())
    if not letters_only:
        return "MAT"
    return letters_only[:3].ljust(3, "X")


def _next_copy_sequence(prefix):
    existing_copy_numbers = PhysicalMaterial.objects.filter(copy_number__startswith=prefix).values_list(
        "copy_number", flat=True
    )
    max_suffix = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    for copy_number in existing_copy_numbers:
        match = pattern.match(copy_number or "")
        if match:
            max_suffix = max(max_suffix, int(match.group(1)))
    return max_suffix + 1

class PhysicalMaterialViewSet(ModelViewSet):
    queryset = PhysicalMaterial.objects.all()
    serializer_class = PhysicalMaterialSerializer
    permission_classes = [IsAuthenticated, IsTechnicalStaffForWrite]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff_profile = _get_staff_profile_or_error(request.user)

        data = serializer.validated_data.copy()
        total_copies = int(data.pop("total_copies"))
        if total_copies < 1:
            raise ValidationError({"total_copies": "total_copies must be at least 1."})

        title = data.get("title")
        prefix = _copy_prefix_from_title(title)

        created_items = []
        with transaction.atomic():
            next_seq = _next_copy_sequence(prefix)
            for offset in range(total_copies):
                copy_number = f"{prefix}{next_seq + offset:03d}"
                created_items.append(
                    PhysicalMaterial.objects.create(
                        **data,
                        total_copies=1,
                        copy_number=copy_number,
                        created_by=staff_profile,
                    )
                )

        output = self.get_serializer(created_items, many=True)
        return Response(
            {"created_count": len(created_items), "items": output.data},
            status=status.HTTP_201_CREATED,
        )

    def perform_update(self, serializer):
        serializer.save()


class DigitalMaterialViewSet(ModelViewSet):
    queryset = DigitalMaterial.objects.all()
    serializer_class = DigitalMaterialSerializer
    permission_classes = [IsAuthenticated, IsTechnicalStaffForWrite]
    parser_classes = [MultiPartParser, FormParser]


    def perform_create(self, serializer):
        serializer.save(created_by=_get_staff_profile_or_error(self.request.user))

    def perform_update(self, serializer):
        serializer.save()
