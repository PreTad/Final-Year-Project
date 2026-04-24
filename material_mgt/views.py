import requests

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
import os
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