from django.utils import timezone

from .models import *
from rest_framework import serializers


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
            "status",
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
            # PhysicalMaterial does not have available_copies; use total_copies for availability checks.
            if material.total_copies <= 0:
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
        validated_data["expiry_date"] = timezone.now() + timezone.timedelta(hours=3)
        validated_data.setdefault("status", "RESERVED")
        return super().create(validated_data)
