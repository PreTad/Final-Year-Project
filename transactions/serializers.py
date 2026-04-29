from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import Borrow, Reservation, Return, PolicyConfiguration
from .services import calculate_overdue_days, finalize_return_for_borrow
from user_mgt.models import User
from .policy import get_policy_configuration


def _norm_role(role):
    return "".join(str(role or "").upper().split())


class ReservationSerializer(serializers.ModelSerializer):

    material_title = serializers.CharField(source="material_id.title", read_only=True)
    material_author = serializers.CharField(source="material_id.author", read_only=True)
    member_id_number = serializers.CharField(source="member.id_number", required=False)
    class Meta:
        model = Reservation
        fields = [
            "id",
            "member",
            "material_id",
            "reserve_date",
            "expiry_date",
            "status",
            "material_title",
            "material_author",
            "member_id_number"
        ]

        read_only_fields = [
            "id",
            "member",
            "reserve_date",
            "expiry_date",
            "status",
            "material_title",
            "material_author",
        ]

    def validate(self, attrs):

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or _norm_role(getattr(user, "role", None)) != "MEMBER":
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
            member=user,
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
        if not user or _norm_role(getattr(user, "role", None)) != "MEMBER":
            raise serializers.ValidationError("Only members can create reservations.")

        validated_data["member"] = user

        policy = get_policy_configuration()
        validated_data["expiry_date"] = timezone.now() + timezone.timedelta(
            hours=policy.reservation_expiry_hours
        )

        validated_data["status"] = "RESERVED"

        return super().create(validated_data)
    
class BorrowSerializer(serializers.ModelSerializer):
    member = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    member_id = serializers.CharField(source="member.id_number", read_only=True)
    material_title = serializers.CharField(source="material.title", read_only=True)
    material_author = serializers.CharField(source="material.author", read_only=True)
    member_name = serializers.CharField(source="member.first_name", read_only=True)
    estimated_fine_amount = serializers.SerializerMethodField()
    is_returned = serializers.SerializerMethodField()
    return_id = serializers.SerializerMethodField()
    returned_at = serializers.SerializerMethodField()
    final_fine_amount = serializers.SerializerMethodField()

    class Meta:
        model = Borrow
        fields = [
            "id",
            "member",
            "member_id",
            "material",
            "reservation",
            "borrow_date",
            "due_date",
            "estimated_fine_amount",
            "status",
            "created_by",
            "material_title",
            "member_name",
            "material_author",
            "is_returned",
            "return_id",
            "returned_at",
            "final_fine_amount",
        ]
        extra_kwargs = {
            "member": {"required": False},
            "material": {"required": False},
        }

        read_only_fields = [
            "id",
            "borrow_date",
            "status",
            "created_by",
            "material_title",
            "material_author",
            "member_name",
            "due_date",
        ]

    def get_is_returned(self, obj):
        return obj.status == "RETURNED"

    def get_return_id(self, obj):
        latest_return = obj.returns.order_by("-return_date").first()
        return latest_return.id if latest_return else None

    def get_returned_at(self, obj):
        if obj.status != "RETURNED":
            return None
        latest_return = obj.returns.order_by("-return_date").first()
        return latest_return.return_date if latest_return else None

    def get_final_fine_amount(self, obj):
        latest_return = obj.returns.order_by("-return_date").first()
        return latest_return.fine_amount if latest_return else None

    def get_estimated_fine_amount(self, obj):
        latest_return = obj.returns.order_by("-return_date").first()
        if latest_return:
            return latest_return.fine_amount

        overdue_days = 3
        policy = get_policy_configuration()
        daily_fine_rate = policy.daily_fine_rate
        return daily_fine_rate * overdue_days

    def validate(self, attrs):
        reservation = attrs.get("reservation")

        # 2. Handle Reservation logic (Overrides member/material)
        if reservation:
            if reservation.status != "RESERVED" or reservation.expiry_date <= timezone.now():
                raise serializers.ValidationError({"reservation": "Reservation is inactive or expired."})
            attrs["member"] = reservation.member
            attrs["material"] = reservation.material_id

        # 3. Final Check on the resolved member
        final_member = attrs.get("member")
        if not final_member:
            raise serializers.ValidationError({"member": "Member is required."})

        # The Logic Gate: Check the role string
        # We use .strip() and .upper() to ensure minor typos don't break it
        user_role = _norm_role(getattr(final_member, "role", ""))
        
        if user_role != "MEMBER":
            raise serializers.ValidationError({
                "member": f"Validation failed. User role is '{getattr(final_member, 'role', 'N/A')}', but 'MEMBER' is required."
            })

        # 4. Material Availability
        material = attrs.get("material")
        if not material:
            raise serializers.ValidationError({"material": "Material is required."})

        # Do not trust cached available_copies alone; compute effective availability.
        active_borrows = Borrow.objects.filter(material=material, returns__isnull=True).count()
        effective_available = material.total_copies - active_borrows
        if effective_available <= 0:
            raise serializers.ValidationError({"material": "No available copies to borrow."})

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or _norm_role(getattr(user, "role", None)) != "STACKSTAFF":
            raise serializers.ValidationError("Only STACK STAFF can create borrows.")

        staff = getattr(user, "staff", None)
        if not staff:
            raise serializers.ValidationError("Staff profile not found.")
        material = validated_data["material"]
        reservation = validated_data.get("reservation")

        with transaction.atomic():
            locked_material = material.__class__.objects.select_for_update().get(pk=material.pk)
            currently_borrowed = Borrow.objects.filter(
                material=locked_material,
                returns__isnull=True,
            ).count()
            available_after_borrow = locked_material.total_copies - (currently_borrowed + 1)

            if available_after_borrow < 0:
                raise serializers.ValidationError({"material": "No available copies to borrow."})

            locked_material.available_copies = available_after_borrow
            locked_material.save(update_fields=["available_copies"])

            # set due date (example: 7 days)
            validated_data["material"] = locked_material
            policy = get_policy_configuration()
            validated_data["due_date"] = timezone.now() + timezone.timedelta(
                minutes=policy.borrow_duration_minutes
            )
            validated_data["created_by"] = staff

            # if borrowed from reservation, expire reservation
            if reservation:
                reservation.status = "EXPIRED"
                reservation.save(update_fields=["status"])

            return super().create(validated_data)

class ReturnSerializer(serializers.ModelSerializer):
    member = serializers.PrimaryKeyRelatedField(source="borrow.member", read_only=True)
    material = serializers.PrimaryKeyRelatedField(source="borrow.material", read_only=True)
    member_name = serializers.CharField(source="borrow.member.first_name", read_only=True)
    material_title = serializers.CharField(source="borrow.material.title", read_only=True)
    due_date = serializers.DateTimeField(source="borrow.due_date", read_only=True)
    payment_status = serializers.SerializerMethodField()
    payment_reference = serializers.SerializerMethodField()

    class Meta:
        model = Return
        fields = [
            "id",
            "borrow",
            "member",
            "member_name",
            "material",
            "material_title",
            "due_date",
            "return_date",
            "fine_amount",
            "created_by",
            "payment_status",
            "payment_reference",
        ]
        read_only_fields = [
            "id",
            "member",
            "member_name",
            "material",
            "material_title",
            "due_date",
            "return_date",
            "fine_amount",
            "created_by",
            "payment_status",
            "payment_reference",
        ]

    def _latest_payment(self, obj):
        return obj.payment.order_by("-payment_date").first()

    def get_payment_status(self, obj):
        latest_payment = self._latest_payment(obj)
        return latest_payment.status if latest_payment else "UNPAID"

    def get_payment_reference(self, obj):
        latest_payment = self._latest_payment(obj)
        return latest_payment.transaction_reference if latest_payment else None

    def validate(self, attrs):
        borrow = attrs.get("borrow")
        if not borrow:
            raise serializers.ValidationError({"borrow": "Borrow is required."})

        if borrow.returns.exists():
            raise serializers.ValidationError({"borrow": "This borrow has already been returned."})

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or _norm_role(getattr(user, "role", None)) != "STACKSTAFF":
            raise serializers.ValidationError("Only STACK STAFF can record returns.")

        staff = getattr(user, "staff", None)
        if not staff:
            raise serializers.ValidationError("Staff profile not found.")

        borrow = validated_data["borrow"]
        now = timezone.now()

        overdue_days = calculate_overdue_days(borrow.due_date, now=now)
        policy = get_policy_configuration()
        daily_fine_rate = policy.daily_fine_rate
        validated_data["fine_amount"] = daily_fine_rate * overdue_days
        validated_data["created_by"] = staff

        return_record = super().create(validated_data)

        # Finalize immediately only when no fine is due.
        # If fine exists, payment verification will finalize the return.
        if return_record.fine_amount <= 0:
            finalize_return_for_borrow(borrow)

        return return_record


class PolicyConfigurationSerializer(serializers.ModelSerializer):
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PolicyConfiguration
        fields = [
            "id",
            "daily_fine_rate",
            "borrow_duration_minutes",
            "reservation_expiry_hours",
            "updated_at",
            "updated_by",
        ]
        read_only_fields = ["id", "updated_at", "updated_by"]
