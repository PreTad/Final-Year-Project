from rest_framework.permissions import BasePermission, SAFE_METHODS


def _norm_role(role):
    return "".join(str(role or "").upper().split())


class IsSuperAdminForWrite(BasePermission):
    """
    Allow authenticated users to read.
    Restrict create/update/delete to users with SUPER ADMIN role.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _norm_role(getattr(user, "role", None)) == "SUPERADMIN"
    

class CanCreateUsers(BasePermission):
    """
    Allow only ADMIN and SUPER ADMIN users to create accounts.
    """
    message = "Only authenticated users with role ADMIN or SUPER ADMIN can create users."

    def has_permission(self, request, view):
        user = request.user
        if request.method == "OPTIONS":
            return True
        if not user or not user.is_authenticated:
            self.message = "Authentication is required."
            return False
        if request.method != "POST":
            self.message = "Only POST is allowed for this endpoint."
            return False
        if _norm_role(getattr(user, "role", None)) not in {"ADMIN", "SUPERADMIN"}:
            self.message = "Your role does not allow user creation. Required role: ADMIN or SUPER ADMIN."
            return False
        return True


class CanDeleteUsers(BasePermission):
    """
    Allow only ADMIN and SUPER ADMIN users to delete accounts.
    ADMIN cannot delete ADMIN/SUPER ADMIN users.
    """
    message = "Only ADMIN or SUPER ADMIN can delete users."

    def has_permission(self, request, view):
        user = request.user
        if request.method == "OPTIONS":
            return True
        if not user or not user.is_authenticated:
            self.message = "Authentication is required."
            return False
        if request.method != "DELETE":
            self.message = "Only DELETE is allowed for this endpoint."
            return False
        if _norm_role(getattr(user, "role", None)) not in {"ADMIN", "SUPERADMIN"}:
            self.message = "Your role does not allow user deletion. Required role: ADMIN or SUPER ADMIN."
            return False
        return True

    def has_object_permission(self, request, view, obj):
        actor_role = _norm_role(getattr(request.user, "role", None))
        target_role = _norm_role(getattr(obj, "role", None))
        if actor_role == "ADMIN" and getattr(request.user, "pk", None) == getattr(obj, "pk", None):
            self.message = "ADMIN cannot delete their own account."
            return False
        if actor_role == "ADMIN" and target_role in {"ADMIN", "SUPERADMIN"}:
            self.message = "ADMIN cannot delete ADMIN or SUPER ADMIN users."
            return False
        return True

class IsTechnicalStaffForWrite(BasePermission):
    """
    Allow authenticated users to read.
    Restrict create/update/delete to TECHNICAL STAFF role.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _norm_role(getattr(user, "role", None)) == "TECHNICALSTAFF"


class IsStackStaffForWrite(BasePermission):
    """
    Allow authenticated users to read.
    Restrict create/update/delete to STACK STAFF role.
    """

    message = "Only STACK STAFF can perform write operations."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _norm_role(getattr(user, "role", None)) == "STACKSTAFF"
