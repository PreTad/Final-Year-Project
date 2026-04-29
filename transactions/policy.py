from decimal import Decimal

from django.conf import settings

from .models import PolicyConfiguration


def get_policy_configuration():
    policy = PolicyConfiguration.objects.order_by("-updated_at").first()
    if policy:
        return policy

    return PolicyConfiguration(
        daily_fine_rate=Decimal(str(getattr(settings, "LIBRARY_DAILY_FINE_RATE", "0"))),
        borrow_duration_minutes=2,
        reservation_expiry_hours=3,
    )
