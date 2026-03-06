from material_mgt.models import *
from rest_framework import serializers

class PhysicalMaterialSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = PhysicalMaterial
        fields = "__all__"
        read_only_fields = ["created_by", "created_by_name", "copy_number"]


class DigitalMaterialSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = DigitalMaterial
        fields = "__all__"
        read_only_fields = ["created_by", "created_by_name", "format", "file_size"]
