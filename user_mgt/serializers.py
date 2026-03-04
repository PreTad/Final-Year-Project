from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import DepartmentHead, Library, Member, Staff, User


def _norm_role(role):
    return "".join(str(role or "").upper().split())


def _get_user_profile(user):
    for rel in ("member", "department_head", "staff"):
        profile = getattr(user, rel, None)
        if profile:
            return profile
    return None


def _build_media_url(request, file_field):
    if not file_field:
        return None
    url = file_field.url
    return request.build_absolute_uri(url) if request else url


class LibrarySerializer(serializers.ModelSerializer):
    staff_id = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.select_related("user_id").filter(user_id__role__in=["ADMIN", "SUPER ADMIN"]),
        required=False,
        allow_null=True,
    )
    staff_name = serializers.SerializerMethodField(read_only=True)

    def get_staff_name(self, obj):
        if not obj.staff_id:
            return None
        return obj.staff_id.full_name or obj.staff_id.user_id.id_number

    class Meta:
        model = Library
        fields = ["id", "name", "campus", "staff_id", "staff_name", "location", "phone"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(write_only=True, required=True, max_length=15)
    department = serializers.CharField(write_only=True, required=False, max_length=70)
    user_type = serializers.ChoiceField(write_only=True, required=False, choices=[c[0] for c in Member.USER_TYPE])

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
            "phone",
            "department",
            "user_type",
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

        if target_role_norm == "MEMBER" and not attrs.get("department"):
            raise serializers.ValidationError({"department": "Department is required when creating a MEMBER."})
        if target_role_norm == "MEMBER" and not attrs.get("user_type"):
            raise serializers.ValidationError({"user_type": "User type is required when creating a MEMBER."})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        phone = validated_data.pop("phone")
        department = validated_data.pop("department", "UNASSIGNED")
        user_type = validated_data.pop("user_type", None)
        role = validated_data.get("role")
        role_norm = _norm_role(role)
        
        with transaction.atomic():
            if role_norm == "SUPERADMIN":
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
                    defaults={"department": department, "user_type": user_type, "phone": phone},
                )
            elif role_norm == "DEPARTMENTHEAD":
                DepartmentHead.objects.get_or_create(
                    user_id=user,
                    defaults={"department": department, "phone": phone},
                )
            elif role_norm in {"STACKSTAFF", "TECHNICALSTAFF", "FRONTDESKSTAFF", "ADMIN", "SUPERADMIN"}:
                Staff.objects.get_or_create(user_id=user, defaults={"phone": phone})

            return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self):
        email = self.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        frontend_base_url = getattr(settings, "PASSWORD_RESET_FRONTEND_URL", "").rstrip("/")

        if frontend_base_url:
            reset_link = f"{frontend_base_url}?uid={uid}&token={token}"
        else:
            reset_link = f"/reset-password?uid={uid}&token={token}"

        send_mail(
            subject="Password Reset Request",
            message=(
                "You requested a password reset for your account.\n\n"
                f"Use this link to reset your password:\n{reset_link}\n\n"
                "If you did not request this, please ignore this email."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
            fail_silently=False,
        )


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"uid": "Invalid reset link."})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "Invalid or expired reset token."})

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class UserMeSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "id_number", "first_name", "last_name", "email", "role", "status", "phone", "photo"]
        read_only_fields = ["id", "id_number", "role", "status", "phone", "photo"]

    def get_phone(self, obj):
        profile = _get_user_profile(obj)
        return getattr(profile, "phone", None)

    def get_photo(self, obj):
        profile = _get_user_profile(obj)
        request = self.context.get("request")
        return _build_media_url(request, getattr(profile, "photo", None))

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        profile = _get_user_profile(self.user)
        request = self.context.get("request")

        # Extra response fields (alongside refresh/access)
        data["user"] = {
            "id": str(self.user.id),
            "id_number": self.user.id_number,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "email": self.user.email,
            "role": self.user.role,
            "status": self.user.status,
            "phone": getattr(profile, "phone", None),
            "photo": _build_media_url(request, getattr(profile, "photo", None)),
        }
        return data
