from rest_framework.generics import CreateAPIView
from rest_framework.generics import DestroyAPIView
from django.contrib.auth import update_session_auth_hash
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import DigitalMaterial, Library, PhysicalMaterial, Reservation, Staff, User
from .permissions import CanCreateUsers, CanDeleteUsers, IsSuperAdminForWrite, IsTechnicalStaffForWrite
from .serializers import (
    ChangePasswordSerializer,
    DigitalMaterialSerializer,
    LibrarySerializer,
    PhysicalMaterialSerializer,
    ReservationSerializer,
    UserMeSerializer,
    UserCreateSerializer,
)


class LibraryViewSet(ModelViewSet):
    queryset = Library.objects.all()
    serializer_class = LibrarySerializer
    permission_classes = [IsAuthenticated, IsSuperAdminForWrite]


class UserCreateAPIView(CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [IsAuthenticated, CanCreateUsers]


class UserDeleteAPIView(DestroyAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, CanDeleteUsers]


def _norm_role(role):
    return "".join(str(role or "").upper().split())


def _get_staff_profile_or_error(user):
    staff_profile = getattr(user, "staff", None)
    if staff_profile:
        return staff_profile
    return Staff.objects.create(user_id=user)


class PhysicalMaterialViewSet(ModelViewSet):
    queryset = PhysicalMaterial.objects.all()
    serializer_class = PhysicalMaterialSerializer
    permission_classes = [IsAuthenticated, IsTechnicalStaffForWrite]

    def perform_create(self, serializer):
        serializer.save(created_by=_get_staff_profile_or_error(self.request.user))

    def perform_update(self, serializer):
        serializer.save()


class DigitalMaterialViewSet(ModelViewSet):
    queryset = DigitalMaterial.objects.all()
    serializer_class = DigitalMaterialSerializer
    permission_classes = [IsAuthenticated, IsTechnicalStaffForWrite]

    def perform_create(self, serializer):
        serializer.save(created_by=_get_staff_profile_or_error(self.request.user))

    def perform_update(self, serializer):
        serializer.save()


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


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            raise ValidationError({"old_password": "Old password is incorrect."})
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        update_session_auth_hash(request, user)
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class UserMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserMeSerializer(request.user).data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserMeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
