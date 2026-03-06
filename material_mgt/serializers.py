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
    file = serializers.FileField(required=True)

    class Meta:
        model = DigitalMaterial
        fields = "__all__"
        read_only_fields = ["created_by", "created_by_name"]

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.method == "POST" and not attrs.get("file"):
            raise serializers.ValidationError({"file": "This field is required for digital material upload."})
        upload = attrs.get("file")
        if upload is not None:
            # Keep existing model fields populated from uploaded file metadata.
            name = str(getattr(upload, "name", ""))
            ext = name.rsplit(".", 1)[-1].upper() if "." in name else "UNKNOWN"
            size_bytes = int(getattr(upload, "size", 0) or 0)
            size_mb = round(size_bytes / (1024 * 1024), 2)
            attrs["format"] = ext
            attrs["file_size"] = f"{size_mb} MB"
        return attrs
