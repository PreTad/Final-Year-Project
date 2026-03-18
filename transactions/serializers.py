from rest_framework import serializers
from django.utils import timezone
from .models import Borrow, Reservation
from user_mgt.models import Member


def _norm_role(role):
    return "".join(str(role or "").upper().split())


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
        member = getattr(user, "member", None)

        if not member:
            raise serializers.ValidationError("Only members can reserve materials.")

        material = attrs.get("material_id")

        if not material:
            raise serializers.ValidationError({"material_id": "Material is required."})

        # If copies are available, user should borrow instead
        if material.available_copies > 0:
            raise serializers.ValidationError(
                {"material_id": "Material is available. Borrow instead."}
            )

        # Prevent duplicate reservation
        existing = Reservation.objects.filter(
            member_id=member,
            material_id=material,
            status="RESERVED",
            expiry_date__gt=timezone.now()
        ).exists()

        if existing:
            raise serializers.ValidationError(
                "You already reserved this material."
            )

        # Limit reservation queue
        total_reservations = Reservation.objects.filter(
            material_id=material,
            status="RESERVED",
            expiry_date__gt=timezone.now()
        ).count()

        if total_reservations >= material.total_copies:
            raise serializers.ValidationError(
                {"material_id": "Reservation queue is full."}
            )

        return attrs

    def create(self, validated_data):

        request = self.context.get("request")
        user = getattr(request, "user", None)
        member = getattr(user, "member", None)

        if not member:
            raise serializers.ValidationError("Only members can create reservations.")

        validated_data["member_id"] = member

        validated_data["expiry_date"] = (
            timezone.now() + timezone.timedelta(hours=3)
        )

        validated_data["status"] = "RESERVED"

        return super().create(validated_data)
    
class BorrowSerializer(serializers.ModelSerializer):
    material_title = serializers.CharField(source="material.title", read_only=True)
    member_name = serializers.CharField(source="member.user_id.first_name", read_only=True)
    member_id_number = serializers.CharField(write_only=True, required=False)
    class Meta:
        model = Borrow
        fields = [
            "id",
            "member",
            "member_id_number",
            "material",
            "reservation",
            "borrow_date",
            "due_date",
            "status",
            "created_by",
            "material_title",
            "member_name",
        ]

        read_only_fields = [
            "id",
            "borrow_date",
            "status",
            "created_by",
            "material_title",
            "member_name",
        ]

    def validate(self, attrs):

        member_id_number = attrs.get("member_id_number")
        member = attrs.get("member")
        if member_id_number and member:
            raise serializers.ValidationError(
                {"member_id_number": "Provide either member or member_id_number, not both."}
            )
        if member_id_number and not member:
            member = Member.objects.filter(user_id__id_number=member_id_number).first()
            if not member:
                raise serializers.ValidationError(
                    {"member_id_number": "No member found with that ID number."}
                )
            attrs["member"] = member

        if not attrs.get("member"):
            raise serializers.ValidationError({"member": "Member is required."})

        material = attrs.get("material")
        reservation = attrs.get("reservation")
        # Check if material has available copies
        if material.available_copies <= 0:
            raise serializers.ValidationError(
                {"material": "No available copies to borrow."}
            )
        # Validate reservation if provided
        if reservation:

            if reservation.status != "RESERVED":
                raise serializers.ValidationError(
                    {"reservation": "Reservation is not active."}
                )

            if reservation.material_id != material:
                raise serializers.ValidationError(
                    {"reservation": "Reservation does not match the material."}
                )

        return attrs

    def create(self, validated_data):

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or _norm_role(getattr(user, "role", None)) != "STACKSTAFF":
            raise serializers.ValidationError("Only STACK STAFF can create borrows.")

        staff = getattr(user, "staff", None)
        if not staff:
            raise serializers.ValidationError("Staff profile not found.")
        validated_data.pop("member_id_number", None)
        material = validated_data["material"]

        # decrease available copies
        material.available_copies -= 1
        material.save()

        # set due date (example: 14 days)
        validated_data["due_date"] = timezone.now() + timezone.timedelta(days=7)
        validated_data["created_by"] = staff
        reservation = validated_data.get("reservation")

        # if borrowed from reservation, expire reservation
        if reservation:
            reservation.status = "EXPIRED"
            reservation.save()

        return super().create(validated_data)    
