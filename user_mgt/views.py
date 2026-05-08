from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import filters, status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from django.db.models import Q

from .access import get_user_library, is_admin_like, is_super_admin, normalize_role
from .models import Library, Staff, User
from .permissions import CanCreateUsers, CanDeleteUsers, IsSuperAdminForWrite
from .serializers import (
    AdminUserListSerializer,
    ChangePasswordSerializer,
    ConfirmResetOTPSerializer,
    ForgotPasswordSerializer,
    LibrarySerializer,
    LibraryPolicySerializer,
    ResetPasswordSerializer,
    UserListSerializer,
    UserMeSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    CustomTokenObtainPairSerializer,
)
from .models import LibraryPolicy

from rest_framework_simplejwt.views import TokenObtainPairView

# --- Authentication Views ---

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


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


# --- Password Reset Flow ---

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
            {"detail": "If an account with that email exists, a password reset OTP has been sent."},
            status=status.HTTP_200_OK,
        )


class ConfirmResetOTPAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ConfirmResetOTPSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"},
                    "expires_in": {"type": "integer"},
                    "confirm_token": {"type": "string"},
                },
            }
        },
    )
    def post(self, request):
        serializer = ConfirmResetOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        
        response = Response(
            {
                "detail": "OTP confirmed.",
                "expires_in": data["expires_in"],
                "confirm_token": data["confirm_token"],
            },
            status=status.HTTP_200_OK,
        )
        
        # Set the confirmation token in an HttpOnly cookie for security
        response.set_cookie(
            "password_reset_confirm_token",
            data["confirm_token"],
            max_age=data["expires_in"],
            httponly=True,
            samesite="Lax",
            secure=not settings.DEBUG,  # True in production
        )
        return response


class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    )
    def post(self, request):
        # We pass the request to context so the serializer can read the cookie
        serializer = ResetPasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        response = Response({"detail": "Password has been reset successfully."}, status=status.HTTP_200_OK)
        # Clean up the session cookie after success
        response.delete_cookie("password_reset_confirm_token")
        return response


# --- Library Management ---

class LibraryViewSet(ModelViewSet):
    queryset = Library.objects.all()
    serializer_class = LibrarySerializer
    permission_classes = [IsAuthenticated, IsSuperAdminForWrite]

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_super_admin(self.request.user):
            return queryset

        actor_library = get_user_library(self.request.user)
        if not actor_library:
            return queryset.none()
        return queryset.filter(pk=actor_library.pk)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if is_super_admin(request.user):
            staffs = (
                Staff.objects.select_related("user_id")
                .filter(user_id__role__in=["ADMIN", "SUPER ADMIN"])
                .order_by("user_id__first_name", "user_id__last_name")
            )
        else:
            actor_library = get_user_library(request.user)
            staffs = (
                Staff.objects.select_related("user_id")
                .filter(user_id__role__in=["ADMIN", "SUPER ADMIN"], user_id__library=actor_library)
                .order_by("user_id__first_name", "user_id__last_name")
            )
        admin_staffs = [
            {
                "id": str(staff.id),
                "staff_id": str(staff.id),
                "user_id": str(staff.user_id.id),
                "name": staff.full_name or staff.user_id.id_number,
                "role": staff.user_id.role,
                "library_id": str(staff.user_id.library_id) if staff.user_id.library_id else None,
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


class LibraryPolicyViewSet(ModelViewSet):
    queryset = LibraryPolicy.objects.select_related("library").all()
    serializer_class = LibraryPolicySerializer
    permission_classes = [IsAuthenticated]

    def _ensure_write_access(self):
        if not is_admin_like(self.request.user):
            raise ValidationError("Only ADMIN or SUPER ADMIN can manage library policies.")

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_super_admin(self.request.user):
            return queryset

        actor_library = get_user_library(self.request.user)
        if not actor_library:
            return queryset.none()
        return queryset.filter(library=actor_library)

    def perform_create(self, serializer):
        self._ensure_write_access()
        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self._ensure_write_access()
        serializer.save()
        return Response(serializer.data)

    partial_update = update

    def perform_destroy(self, instance):
        self._ensure_write_access()
        instance.delete()


# --- User Management ---

class UserCreateAPIView(CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [IsAuthenticated, CanCreateUsers]


class UserDeleteAPIView(DestroyAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, CanDeleteUsers]


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="role",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filter users by role. Example values: ADMIN, MEMBER, SUPER ADMIN",
        ),
        OpenApiParameter(
            name="search",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Search by first name or id.",
        ),
    ]
)
class UserListAPIView(ListAPIView):
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['^first_name', '=id_number']

    def get_queryset(self):
        queryset = User.objects.all().order_by("first_name", "last_name", "id_number")
        role = self.request.query_params.get("role")
        search = self.request.query_params.get("search")
        actor = self.request.user
        actor_role = " ".join(
        normalize_role(getattr(actor, "role", "")).upper().split())
        
        if role:
            normalized_role = " ".join(role.upper().split())
            if normalized_role == "STACKSTAFF":
                normalized_role = "STACK STAFF"
            elif normalized_role == "TECHNICALSTAFF":
                normalized_role = "TECHNICAL STAFF"
            elif normalized_role == "FRONTDESKSTAFF":
                normalized_role = "FRONT DESK STAFF"
            elif normalized_role == "SUPERADMIN":
                normalized_role = "SUPER ADMIN"
            elif normalized_role == "DEPARTMENTHEAD":
                normalized_role = "DEPARTMENT HEAD"

            queryset = queryset.filter(role__iexact=normalized_role).order_by("first_name", "last_name", "id_number")
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(id_number__icontains=search)
                | Q(email__icontains=search)
            )
        if actor_role != "SUPERADMIN":
            actor_library = get_user_library(actor)
            if actor_role == "ADMIN" or actor_role == "STACKSTAFF" or actor_role == "TECHNICALSTAFF" or actor_role == "FRONTDESKSTAFF":
                if actor_library:
                    queryset = queryset.filter(library=actor_library)
                else:
                    queryset = queryset.filter(pk=actor.pk)
            elif actor_library:
                queryset = queryset.filter(library=actor_library)
            else:
                queryset = queryset.filter(pk=actor.pk)
        
        return queryset


class UserUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if not is_admin_like(request.user):
            return Response({"detail": "Only ADMIN or SUPER ADMIN can update users."}, status=status.HTTP_403_FORBIDDEN)

        if not is_super_admin(request.user):
            actor_library = get_user_library(request.user)
            if not actor_library or user.library_id != actor_library.id:
                return Response({"detail": "You can only update users in your library."}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserUpdateSerializer(user, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserListSerializer(user, context={"request": request}).data, status=status.HTTP_200_OK)


class AdminUsersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        staffs = (
            Staff.objects.select_related("user_id")
            .filter(user_id__role__in=["ADMIN"])
            .order_by("user_id__first_name", "user_id__last_name")
        )
        if not is_super_admin(request.user):
            actor_library = get_user_library(request.user)
            staffs = staffs.filter(Q(user_id__library=actor_library) | Q(user_id__library__isnull=True))
        data = [
            {
                "staff_id": str(staff.id),
                "name": staff.full_name or staff.user_id.id_number,
                "role": staff.user_id.role,
                "user_id": str(staff.user_id.id),
                "library_id": str(staff.user_id.library_id) if staff.user_id.library_id else None,
            }
            for staff in staffs
        ]
        return Response(data, status=status.HTTP_200_OK)


class UserMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserMeSerializer(request.user, context={"request": request}).data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserMeSerializer(request.user, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
