import requests
from django.db.models import Avg, Count, Q

from rest_framework.generics import CreateAPIView
from rest_framework.generics import DestroyAPIView
from django.contrib.auth import update_session_auth_hash
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import os
from material_mgt.models import *
from material_mgt.serializers import *
from user_mgt.access import get_user_library, is_super_admin, normalize_role
from user_mgt.models import Staff
from user_mgt.permissions import *
# Create your views here.


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _resolve_material_or_error(material_type, material_id):
    material_type_norm = str(material_type or "").strip().lower()

    if material_type_norm == "physical":
        material = PhysicalMaterial.objects.filter(pk=material_id).first()
        if not material:
            raise ValidationError({"material_id": "Physical material not found."})
        return material_type_norm, material

    if material_type_norm == "digital":
        material = DigitalMaterial.objects.filter(pk=material_id).first()
        if not material:
            raise ValidationError({"material_id": "Digital material not found."})
        return material_type_norm, material

    raise ValidationError({"material_type": "Use either 'physical' or 'digital'."})


def _user_can_access_material(user, material):
    if is_super_admin(user):
        return True
    user_library = get_user_library(user)
    return bool(user_library and getattr(material, "library_id", None) == user_library.id)


class IsOwnerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user_id == request.user.id


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
    if normalize_role(getattr(user, "role", None)) not in staff_roles:
        raise ValidationError({"detail": "Only staff-role users can create materials."})

    return Staff.objects.create(user_id=user)

class PhysicalMaterialViewSet(ModelViewSet):
    queryset = PhysicalMaterial.objects.select_related("library", "created_by__user_id").all()
    serializer_class = PhysicalMaterialSerializer
    # permission_classes = [IsAuthenticated, IsTechnicalStaffForWrite]

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_super_admin(self.request.user):
            return queryset

        actor_library = get_user_library(self.request.user)
        if not actor_library:
            return queryset.none()
        return queryset.filter(library=actor_library)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff_profile = _get_staff_profile_or_error(request.user)
        actor_library = get_user_library(request.user)
        if not actor_library and not is_super_admin(request.user):
            raise ValidationError({"library": "Your account is not assigned to a library yet."})

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
            library=data.get("library") if is_super_admin(request.user) else actor_library,
        )
        output = self.get_serializer(material)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        actor_library = get_user_library(self.request.user)
        if not actor_library and not is_super_admin(self.request.user):
            raise ValidationError({"library": "Your account is not assigned to a library yet."})
        serializer.save(
            library=serializer.validated_data.get("library") if is_super_admin(self.request.user) else actor_library
        )


class DigitalMaterialViewSet(ModelViewSet):
    queryset = DigitalMaterial.objects.select_related("library", "created_by__user_id").all()
    serializer_class = DigitalMaterialSerializer
    # permission_classes = [IsAuthenticated, IsTechnicalStaffForWrite]

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_super_admin(self.request.user):
            return queryset

        actor_library = get_user_library(self.request.user)
        if not actor_library:
            return queryset.none()
        return queryset.filter(library=actor_library)

    def perform_create(self, serializer):
        actor_library = get_user_library(self.request.user)
        if not actor_library and not is_super_admin(self.request.user):
            raise ValidationError({"library": "Your account is not assigned to a library yet."})
        serializer.save(
            created_by=_get_staff_profile_or_error(self.request.user),
            library=serializer.validated_data.get("library") if is_super_admin(self.request.user) else actor_library,
        )

    def perform_update(self, serializer):
        actor_library = get_user_library(self.request.user)
        if not actor_library and not is_super_admin(self.request.user):
            raise ValidationError({"library": "Your account is not assigned to a library yet."})
        serializer.save(
            library=serializer.validated_data.get("library") if is_super_admin(self.request.user) else actor_library
        )


class MaterialFeedbackViewSet(ModelViewSet):
    serializer_class = MaterialFeedbackSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    queryset = MaterialFeedback.objects.select_related("user", "physical_material", "digital_material")

    def get_queryset(self):
        queryset = self.queryset

        material_type = self.request.query_params.get("material_type")
        material_id = self.request.query_params.get("material_id")
        mine_only = _parse_bool(self.request.query_params.get("mine"), default=False)

        if mine_only:
            queryset = queryset.filter(user=self.request.user)

        if bool(material_type) ^ bool(material_id):
            raise ValidationError(
                {"detail": "Provide material_type and material_id together."}
            )

        if material_type and material_id:
            material_type_norm = material_type.strip().lower()
            if material_type_norm == "physical":
                queryset = queryset.filter(physical_material_id=material_id)
            elif material_type_norm == "digital":
                queryset = queryset.filter(digital_material_id=material_id)
            else:
                raise ValidationError({"material_type": "Use either 'physical' or 'digital'."})

        return queryset

    def perform_create(self, serializer):
        target_material = serializer.validated_data.get("physical_material") or serializer.validated_data.get("digital_material")
        if target_material and not _user_can_access_material(self.request.user, target_material):
            raise ValidationError({"detail": "You can only comment on materials from your library."})
        serializer.save(user=self.request.user)


class MaterialFavoriteViewSet(ModelViewSet):
    serializer_class = MaterialFavoriteSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    queryset = MaterialFavorite.objects.select_related("user", "physical_material", "digital_material")

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)

        material_type = self.request.query_params.get("material_type")
        material_id = self.request.query_params.get("material_id")
        if bool(material_type) ^ bool(material_id):
            raise ValidationError(
                {"detail": "Provide material_type and material_id together."}
            )
        if material_type and material_id:
            material_type_norm = material_type.strip().lower()
            if material_type_norm == "physical":
                queryset = queryset.filter(physical_material_id=material_id)
            elif material_type_norm == "digital":
                queryset = queryset.filter(digital_material_id=material_id)
            else:
                raise ValidationError({"material_type": "Use either 'physical' or 'digital'."})

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        physical_material = serializer.validated_data.get("physical_material")
        digital_material = serializer.validated_data.get("digital_material")
        target_material = physical_material or digital_material
        if target_material and not _user_can_access_material(request.user, target_material):
            raise ValidationError({"detail": "You can only favorite materials from your library."})

        favorite, created = MaterialFavorite.objects.get_or_create(
            user=request.user,
            physical_material=physical_material,
            digital_material=digital_material,
        )

        output = self.get_serializer(favorite)
        return Response(
            output.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MaterialBookmarkViewSet(ModelViewSet):
    serializer_class = MaterialBookmarkSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    queryset = MaterialBookmark.objects.select_related("user", "physical_material", "digital_material")

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)

        material_type = self.request.query_params.get("material_type")
        material_id = self.request.query_params.get("material_id")
        if bool(material_type) ^ bool(material_id):
            raise ValidationError(
                {"detail": "Provide material_type and material_id together."}
            )
        if material_type and material_id:
            material_type_norm = material_type.strip().lower()
            if material_type_norm == "physical":
                queryset = queryset.filter(physical_material_id=material_id)
            elif material_type_norm == "digital":
                queryset = queryset.filter(digital_material_id=material_id)
            else:
                raise ValidationError({"material_type": "Use either 'physical' or 'digital'."})

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        physical_material = serializer.validated_data.get("physical_material")
        digital_material = serializer.validated_data.get("digital_material")
        target_material = physical_material or digital_material
        if target_material and not _user_can_access_material(request.user, target_material):
            raise ValidationError({"detail": "You can only bookmark materials from your library."})

        bookmark, created = MaterialBookmark.objects.get_or_create(
            user=request.user,
            physical_material=physical_material,
            digital_material=digital_material,
        )

        output = self.get_serializer(bookmark)
        return Response(
            output.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MaterialInteractionStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        material_type = request.query_params.get("material_type")
        material_id = request.query_params.get("material_id")

        if not material_type or not material_id:
            raise ValidationError({"detail": "material_type and material_id are required."})

        material_type_norm, material = _resolve_material_or_error(material_type, material_id)
        if not _user_can_access_material(request.user, material):
            raise ValidationError({"detail": "You can only access interaction stats for materials in your library."})

        feedback_qs = MaterialFeedback.objects.all()
        favorites_qs = MaterialFavorite.objects.all()
        bookmarks_qs = MaterialBookmark.objects.all()

        if material_type_norm == "physical":
            feedback_qs = feedback_qs.filter(physical_material=material)
            favorites_qs = favorites_qs.filter(physical_material=material)
            bookmarks_qs = bookmarks_qs.filter(physical_material=material)
            mine_filter = {"physical_material": material, "user": request.user}
        else:
            feedback_qs = feedback_qs.filter(digital_material=material)
            favorites_qs = favorites_qs.filter(digital_material=material)
            bookmarks_qs = bookmarks_qs.filter(digital_material=material)
            mine_filter = {"digital_material": material, "user": request.user}

        aggregate = feedback_qs.aggregate(
            average_rating=Avg("rating"),
            ratings_count=Count("id"),
            comments_count=Count("id", filter=~Q(comment="")),
        )

        my_feedback = MaterialFeedback.objects.filter(**mine_filter).first()

        return Response(
            {
                "material_type": material_type_norm,
                "material_id": str(material.id),
                "material_title": material.title,
                "average_rating": round(float(aggregate["average_rating"] or 0), 2),
                "ratings_count": int(aggregate["ratings_count"] or 0),
                "comments_count": int(aggregate["comments_count"] or 0),
                "favorites_count": favorites_qs.count(),
                "bookmarks_count": bookmarks_qs.count(),
                "is_favorited": MaterialFavorite.objects.filter(**mine_filter).exists(),
                "is_bookmarked": MaterialBookmark.objects.filter(**mine_filter).exists(),
                "my_rating": my_feedback.rating if my_feedback else None,
                "my_comment": my_feedback.comment if my_feedback else "",
            },
            status=status.HTTP_200_OK,
        )




class GenerateMaterialDescriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        title = str(request.data.get("title", "")).strip()
        author = str(request.data.get("author", "")).strip()

        if not title or not author:
            raise ValidationError({"detail": "Both title and author are required."})

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return Response(
                {"detail": "AI description service is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        model = os.getenv("OPENAI_DESCRIPTION_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"

        prompt = (
            f"Title: {title}\n"
            f"Author: {author}\n\n"
            "Write a concise, helpful library catalog description (80-130 words). "
            "Use clear, neutral language and avoid inventing specific facts."
        )

        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": prompt,
                    "temperature": 0.7,
                    "max_output_tokens": 220,
                },
                timeout=30,
            )
        except requests.RequestException:
            return Response(
                {"detail": "Failed to reach AI provider."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Handle HTTP errors from provider
        if response.status_code >= 400:
            try:
                provider_error = response.json().get("error", {}).get("message", "")
            except Exception:
                provider_error = ""

            return Response(
                {"detail": provider_error or "AI provider returned an error."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Parse response safely (Responses API format)
        try:
            payload = response.json()
        except ValueError:
            return Response(
                {"detail": "Invalid AI provider response."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            description = payload["output"][0]["content"][0]["text"].strip()
        except (KeyError, IndexError, TypeError):
            description = ""

        # Fallback if AI returns empty
        if not description:
            description = f"{title} by {author} is a library material available for borrowing."

        return Response(
            {
                "description": description,
                "model": model,
            },
            status=status.HTTP_200_OK,
        )
