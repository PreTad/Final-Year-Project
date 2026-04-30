from material_mgt.models import *
from rest_framework import serializers

class PhysicalMaterialSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    library_name = serializers.CharField(source="library.name", read_only=True)

    class Meta:
        model = PhysicalMaterial
        fields = "__all__"
        read_only_fields = ["created_by", "created_by_name", "library_name"]


class DigitalMaterialSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    library_name = serializers.CharField(source="library.name", read_only=True)
    file = serializers.FileField(required=True)

    class Meta:
        model = DigitalMaterial
        fields = "__all__"
        read_only_fields = ["created_by", "created_by_name", "library_name", "format","file_size"]

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


MATERIAL_TYPE_CHOICES = (("physical", "physical"), ("digital", "digital"))


class MaterialTargetMixinSerializer(serializers.ModelSerializer):
    material_type = serializers.ChoiceField(choices=MATERIAL_TYPE_CHOICES, write_only=True, required=True)
    material_id = serializers.UUIDField(write_only=True, required=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    user_name = serializers.SerializerMethodField(read_only=True)
    material_title = serializers.SerializerMethodField(read_only=True)

    def get_user_name(self, obj):
        user = getattr(obj, "user", None)
        if not user:
            return None
        return f"{user.first_name} {user.last_name}".strip() or user.id_number

    def get_material_title(self, obj):
        material = obj.physical_material or obj.digital_material
        return getattr(material, "title", None)

    def _set_material_target(self, attrs, material_type, material_id):
        if material_type == "physical":
            material = PhysicalMaterial.objects.filter(pk=material_id).first()
            if not material:
                raise serializers.ValidationError({"material_id": "Physical material not found."})
            attrs["physical_material"] = material
            attrs["digital_material"] = None
        elif material_type == "digital":
            material = DigitalMaterial.objects.filter(pk=material_id).first()
            if not material:
                raise serializers.ValidationError({"material_id": "Digital material not found."})
            attrs["digital_material"] = material
            attrs["physical_material"] = None
        else:
            raise serializers.ValidationError({"material_type": "Invalid material type."})

    def validate(self, attrs):
        attrs = super().validate(attrs)
        material_type = attrs.pop("material_type", None)
        material_id = attrs.pop("material_id", None)

        if self.instance is None:
            if not material_type or not material_id:
                raise serializers.ValidationError(
                    {"detail": "Both material_type and material_id are required."}
                )
            self._set_material_target(attrs, material_type, material_id)
        elif material_type is not None or material_id is not None:
            if not material_type or not material_id:
                raise serializers.ValidationError(
                    {"detail": "Provide both material_type and material_id together when updating target."}
                )
            self._set_material_target(attrs, material_type, material_id)

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.physical_material_id:
            data["material_type"] = "physical"
            data["material_id"] = str(instance.physical_material_id)
        else:
            data["material_type"] = "digital"
            data["material_id"] = str(instance.digital_material_id)
        return data


class MaterialFeedbackSerializer(MaterialTargetMixinSerializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    class Meta:
        model = MaterialFeedback
        fields = [
            "id",
            "user_id",
            "user_name",
            "material_type",
            "material_id",
            "material_title",
            "rating",
            "comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_id", "user_name", "material_title", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if self.instance is None and user and user.is_authenticated:
            exists = MaterialFeedback.objects.filter(
                user=user,
                physical_material=attrs.get("physical_material"),
                digital_material=attrs.get("digital_material"),
            ).exists()
            if exists:
                raise serializers.ValidationError(
                    {"detail": "You already rated this material. Use PATCH to update."}
                )

        return attrs


class MaterialFavoriteSerializer(MaterialTargetMixinSerializer):
    class Meta:
        model = MaterialFavorite
        fields = [
            "id",
            "user_id",
            "user_name",
            "material_type",
            "material_id",
            "material_title",
            "created_at",
        ]
        read_only_fields = ["id", "user_id", "user_name", "material_title", "created_at"]


class MaterialBookmarkSerializer(MaterialTargetMixinSerializer):
    class Meta:
        model = MaterialBookmark
        fields = [
            "id",
            "user_id",
            "user_name",
            "material_type",
            "material_id",
            "material_title",
            "created_at",
        ]
        read_only_fields = ["id", "user_id", "user_name", "material_title", "created_at"]
