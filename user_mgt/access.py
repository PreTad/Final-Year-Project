from .models import Library, LibraryPolicy


STAFF_ROLE_KEYS = {
    "STACKSTAFF",
    "TECHNICALSTAFF",
    "FRONTDESKSTAFF",
    "ADMIN",
    "SUPERADMIN",
}


def normalize_role(role):
    return "".join(str(role or "").upper().split())


def is_super_admin(user):
    return normalize_role(getattr(user, "role", None)) == "SUPERADMIN"


def is_admin_like(user):
    return normalize_role(getattr(user, "role", None)) in {"ADMIN", "SUPERADMIN"}


def is_staff_like(user):
    return normalize_role(getattr(user, "role", None)) in {
        "STACKSTAFF",
        "TECHNICALSTAFF",
        "FRONTDESKSTAFF",
        "ADMIN",
        "SUPERADMIN",
    }


def get_user_library(user):
    library = getattr(user, "library", None)
    return library


def get_active_library_policy(library=None):
    queryset = LibraryPolicy.objects.select_related("library")

    if library is not None:
        policy = (
            queryset.filter(library=library, is_active=True).first()
            or queryset.filter(library=library).first()
        )
        if policy:
            return policy

    return (
        queryset.filter(library__isnull=True, is_active=True).first()
        or queryset.filter(library__isnull=True).first()
    )
