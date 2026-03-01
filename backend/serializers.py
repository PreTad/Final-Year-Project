from rest_framework import serializers
from django.db import transaction

from django.utils import timezone

from .models import DepartmentHead, DigitalMaterial, Library, Member, PhysicalMaterial, Reservation, Staff, User


def _norm_role(role):
    return "".join(str(role or "").upper().split())


class LibrarySerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(read_only=True)

    class Meta:
        model = Library
        fields = ["id", "name", "campus", "staff_id", "staff_name"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "id_number",
            "first_name",
            "last_name",
            "email",
            "role",
            "status",
            "password",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        request = self.context.get("request")
        creator = getattr(request, "user", None)
        target_role = attrs.get("role")
        creator_role = _norm_role(getattr(creator, "role", None))
        target_role_norm = _norm_role(target_role)

        if creator_role == "ADMIN" and target_role_norm in {"ADMIN", "SUPERADMIN"}:
            raise serializers.ValidationError("ADMIN users cannot create ADMIN or SUPER ADMIN accounts.")

        if creator_role not in {"ADMIN", "SUPERADMIN"}:
            raise serializers.ValidationError("Only ADMIN or SUPER ADMIN can create users.")

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        role = validated_data.get("role")
        role_norm = _norm_role(role)
        
        with transaction.atomic():
            if role_norm == "SUPER ADMIN":
                user = User.objects.create_superuser(password=password, **validated_data)
            elif role_norm == "ADMIN":
                validated_data.setdefault("is_staff", True)
                validated_data.setdefault("is_superuser", False)
                user = User.objects.create_user(password=password, **validated_data)
            else:
                validated_data.setdefault("is_staff", False)
                validated_data.setdefault("is_superuser", False)
                user = User.objects.create_user(password=password, **validated_data)

            if role_norm == "MEMBER":
                Member.objects.get_or_create(
                    user_id=user,
                    defaults={"department": "UNASSIGNED", "user_type": "STUDENT"},
                )
            elif role_norm == "DEPARTMENT HEAD":
                DepartmentHead.objects.get_or_create(
                    user_id=user,
                    defaults={"department": "UNASSIGNED"},
                )
            elif role_norm in {"STACK STAFF", "TECHNICAL STAFF", "FRONTDESK STAFF", "ADMIN", "SUPER ADMIN"}:
                Staff.objects.get_or_create(user_id=user)

            return user


class PhysicalMaterialSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = PhysicalMaterial
        fields = "__all__"
        read_only_fields = ["created_by", "created_by_name"]


class DigitalMaterialSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = DigitalMaterial
        fields = "__all__"
        read_only_fields = ["created_by", "created_by_name"]


class ReservationSerializer(serializers.ModelSerializer):
    material_title = serializers.CharField(source="material_id.title", read_only=True)
    material_author = serializers.CharField(source="material_id.author", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "member_id",
            "material_id",
            "reserve_date",
            "expiry_date",
            "status",
            "material_title",
            "material_author",
        ]
        read_only_fields = [
            "id",
            "member_id",
            "reserve_date",
            "expiry_date",
            "material_title",
            "material_author",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        instance = getattr(self, "instance", None)

        if instance is None:
            material = attrs.get("material_id")
            if material is None:
                raise serializers.ValidationError({"material_id": "Material is required."})
            if not material.can_borrow:
                raise serializers.ValidationError({"material_id": "This material cannot be reserved."})
            if material.available_copies <= 0:
                raise serializers.ValidationError({"material_id": "No available copies for reservation."})

            member = getattr(user, "member", None)
            if not member:
                raise serializers.ValidationError("Only members can create reservations.")
            existing = Reservation.objects.filter(
                member_id=member,
                material_id=material,
                status="RESERVED",
            ).exists()
            if existing:
                raise serializers.ValidationError("You already have an active reservation for this material.")

        else:
            # Restrict member updates to cancel only.
            member = getattr(user, "member", None)
            if member and instance.member_id_id == member.id:
                new_status = attrs.get("status")
                if new_status and new_status != "CANCELLED":
                    raise serializers.ValidationError({"status": "Members can only cancel reservations."})

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        member = getattr(user, "member", None)
        if not member:
            raise serializers.ValidationError("Only members can create reservations.")
        validated_data["member_id"] = member
        validated_data["expiry_date"] = timezone.now() + timezone.timedelta(hours=24)
        validated_data.setdefault("status", "RESERVED")
        return super().create(validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)


class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "id_number", "first_name", "last_name", "email", "role", "status"]
        read_only_fields = ["id", "id_number", "role", "status"]
