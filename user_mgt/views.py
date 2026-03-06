from rest_framework.generics import CreateAPIView
from rest_framework.generics import DestroyAPIView
from rest_framework.generics import ListAPIView
from django.contrib.auth import update_session_auth_hash
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from drf_spectacular.utils import extend_schema

from .models import Library, Staff, User
from .permissions import CanCreateUsers, CanDeleteUsers, IsSuperAdminForWrite
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LibrarySerializer,
    ResetPasswordSerializer,
    UserListSerializer,
    UserMeSerializer,
    UserCreateSerializer,
)

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class LibraryViewSet(ModelViewSet):
    queryset = Library.objects.all()
    serializer_class = LibrarySerializer
    permission_classes = [IsAuthenticated, IsSuperAdminForWrite]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        staffs = (
            Staff.objects.select_related("user_id")
            .filter(user_id__role__in=["ADMIN", "SUPER ADMIN"])
            .order_by("user_id__first_name", "user_id__last_name")
        )
        admin_staffs = [
            {
                "id": str(staff.id),
                "name": staff.full_name or staff.user_id.id_number,
                "role": staff.user_id.role,
            }
            for staff in staffs
        ]

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["libraries"] = serializer.data
            response.data["admin_staffs"] = admin_staffs
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({"libraries": serializer.data, "admin_staffs": admin_staffs}, status=status.HTTP_200_OK)


class UserCreateAPIView(CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [IsAuthenticated, CanCreateUsers]

# class GetA
class UserDeleteAPIView(DestroyAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, CanDeleteUsers]


class UserListAPIView(ListAPIView):
    queryset = User.objects.all().order_by("first_name", "last_name", "id_number")
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]


class AdminUsersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        staffs = (
            Staff.objects.select_related("user_id")
            .filter(user_id__role__in=["ADMIN", "SUPER ADMIN"])
            .order_by("user_id__first_name", "user_id__last_name")
        )
        data = [
            {
                "staff_id": str(staff.id),
                "name": staff.full_name or staff.user_id.id_number,
                "role": staff.user_id.role,
                "user_id": str(staff.user_id.id),
            }
            for staff in staffs
        ]
        return Response(data, status=status.HTTP_200_OK)


def _norm_role(role):
    return "".join(str(role or "").upper().split())


def _get_staff_profile_or_error(user):
    staff_profile = getattr(user, "staff", None)
    if staff_profile:
        return staff_profile
    return Staff.objects.create(user_id=user)


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


class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "If an account with that email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password has been reset successfully."}, status=status.HTTP_200_OK)


class UserMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserMeSerializer(request.user).data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserMeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
