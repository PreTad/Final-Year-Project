from django.contrib import admin
from . import models
from django.core.exceptions import PermissionDenied


def _norm_role(role):
    return "".join(str(role or "").upper().split())


class UserAdmin(admin.ModelAdmin):
    list_display = ("id_number", "first_name", "last_name", "email", "role", "status", "is_staff", "is_superuser")
    search_fields = ("id_number", "first_name", "last_name", "email")
    list_filter = ("role", "status", "is_staff", "is_superuser")

    def _actor_can_manage_users(self, request):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return _norm_role(getattr(request.user, "role", None)) in {"ADMIN", "SUPERADMIN"}

    def has_add_permission(self, request):
        return self._actor_can_manage_users(request)

    def has_change_permission(self, request, obj=None):
        return self._actor_can_manage_users(request)

    def has_delete_permission(self, request, obj=None):
        return self._actor_can_manage_users(request)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        actor_role = _norm_role(getattr(request.user, "role", None))
        if "role" in form.base_fields and actor_role == "ADMIN":
            form.base_fields["role"].choices = [
                choice for choice in form.base_fields["role"].choices
                if choice[0] not in {"ADMIN", "SUPER ADMIN"}
            ]
        return form

    def save_model(self, request, obj, form, change):
        actor_role = _norm_role(getattr(request.user, "role", None))
        if actor_role == "ADMIN" and _norm_role(obj.role) in {"ADMIN", "SUPERADMIN"}:
            raise PermissionDenied("ADMIN users cannot create or update ADMIN/SUPER ADMIN accounts.")
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        actor_role = _norm_role(getattr(request.user, "role", None))
        target_role = _norm_role(getattr(obj, "role", None))
        if actor_role == "ADMIN" and request.user.pk == obj.pk:
            raise PermissionDenied("ADMIN cannot delete their own account.")
        if actor_role == "ADMIN" and target_role in {"ADMIN", "SUPERADMIN"}:
            raise PermissionDenied("ADMIN users cannot delete ADMIN or SUPER ADMIN accounts.")
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        actor_role = _norm_role(getattr(request.user, "role", None))
        if actor_role == "ADMIN" and queryset.filter(pk=request.user.pk).exists():
            raise PermissionDenied("ADMIN cannot delete their own account.")
        if actor_role == "ADMIN" and queryset.filter(role__in=["ADMIN", "SUPER ADMIN"]).exists():
            raise PermissionDenied("ADMIN users cannot bulk-delete ADMIN or SUPER ADMIN accounts.")
        super().delete_queryset(request, queryset)


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Member)
admin.site.register(models.DepartmentHead)
admin.site.register(models.Staff)
admin.site.register(models.Notification)
admin.site.register(models.Library)
