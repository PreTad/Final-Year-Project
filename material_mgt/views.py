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
from user_mgt.permissions import *
# Create your views here.

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
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        serializer.save(created_by=_get_staff_profile_or_error(self.request.user))

    def perform_update(self, serializer):
        serializer.save()
