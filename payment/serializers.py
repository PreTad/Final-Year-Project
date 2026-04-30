from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from .models import Payment
from transactions.models import Return
from user_mgt.models import Member

class PaymentSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member_id.user_id.first_name", read_only=True)
    member_email = serializers.CharField(source="member_id.user_id.email", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "member_id", "member_name", "member_email", 
            "return_id", "fine_amount", "payment_date", 
            "method", "transaction_reference", "status",
        ]
        read_only_fields = [
            "id", "member_name", "member_email", "fine_amount", 
            "payment_date", "method", "transaction_reference", "status",
        ]

class ChapaInitPaymentSerializer(serializers.Serializer):
    return_id = serializers.UUIDField()
    callback_url = serializers.URLField(required=False)
    return_url = serializers.URLField(required=False)

    def validate_return_id(self, value):
        if not Return.objects.filter(id=value).exists():
            raise serializers.ValidationError("Return record not found.")
        return value

    def validate(self, attrs):
        return_obj = Return.objects.select_related("borrow__member").get(id=attrs["return_id"])
        member_user = return_obj.borrow.member
        fine_amount = return_obj.fine_amount

        if fine_amount is None:
            raise serializers.ValidationError({"return_id": "Return does not have a fine amount."})

        try:
            amount = Decimal(str(fine_amount))
        except (InvalidOperation, TypeError):
            raise serializers.ValidationError({"return_id": "Invalid fine amount on return."})

        if amount <= 0:
            raise serializers.ValidationError({"return_id": "This return has no payable fine."})

        member_profile = Member.objects.filter(user_id=member_user).first()
        if not member_profile:
            raise serializers.ValidationError({"return_id": "Member profile not found."})

        attrs["return_obj"] = return_obj
        attrs["member_profile"] = member_profile
        attrs["amount"] = amount
        return attrs
