from dataclasses import dataclass, field
from typing import List

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Borrow, Reservation


@dataclass
class OverdueNotificationSummary:
    scanned: int = 0
    status_updated: int = 0
    emailed: int = 0
    skipped_missing_email: int = 0
    errors: List[str] = field(default_factory=list)


def process_overdue_borrows_and_notify():
    now = timezone.now()
    summary = OverdueNotificationSummary()

    overdue_qs = Borrow.objects.select_related("member", "material").filter(
        returns__isnull=True,
        due_date__lt=now,
    )
    summary.scanned = overdue_qs.count()

    # Keep borrow status aligned with current time.
    summary.status_updated = overdue_qs.exclude(status="OVERDUE").update(status="OVERDUE")

    to_notify = overdue_qs.filter(overdue_notified_at__isnull=True)
    for borrow in to_notify:
        member_email = (borrow.member.email or "").strip()
        if not member_email:
            summary.skipped_missing_email += 1
            continue

        overdue_days = (now.date() - borrow.due_date.date()).days
        member_name = (borrow.member.first_name or borrow.member.id_number).strip()
        subject = "Library Notice: Borrowed Material Is Overdue"
        message = (
            f"Dear {member_name},\n\n"
            f"This is a reminder that your borrowed material "
            f"'{borrow.material.title}' became overdue on "
            f"{borrow.due_date.date().isoformat()}.\n"
            f"It is currently {overdue_days} day(s) overdue.\n\n"
            "Please return it as soon as possible to avoid additional fines.\n\n"
            "Thank you."
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[member_email],
                fail_silently=False,
            )
            borrow.overdue_notified_at = now
            borrow.save(update_fields=["overdue_notified_at"])
            summary.emailed += 1
        except Exception as exc:
            summary.errors.append(f"Borrow {borrow.id}: {exc}")

    return summary


@dataclass
class ReservationAvailabilitySummary:
    queued: int = 0
    notified: int = 0
    skipped_missing_email: int = 0
    errors: List[str] = field(default_factory=list)


def notify_reserved_members_material_available(material):
    now = timezone.now()
    summary = ReservationAvailabilitySummary()

    open_slots = max(int(getattr(material, "available_copies", 0)), 0)
    if open_slots <= 0:
        return summary

    reservations = Reservation.objects.select_related("member").filter(
        material_id=material,
        status="RESERVED",
        expiry_date__gt=now,
        availability_notified_at__isnull=True,
    ).order_by("reserve_date")[:open_slots]

    summary.queued = len(reservations)
    for reservation in reservations:
        member_email = (reservation.member.email or "").strip()
        if not member_email:
            summary.skipped_missing_email += 1
            continue

        member_name = (reservation.member.first_name or reservation.member.id_number).strip()
        subject = "Library Notice: Reserved Material Is Now Available"
        message = (
            f"Dear {member_name},\n\n"
            f"The material you reserved, '{material.title}', is now available.\n"
            "Please borrow it as soon as possible before your reservation expires.\n\n"
            "Thank you."
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[member_email],
                fail_silently=False,
            )
            reservation.availability_notified_at = now
            reservation.save(update_fields=["availability_notified_at"])
            summary.notified += 1
        except Exception as exc:
            summary.errors.append(f"Reservation {reservation.id}: {exc}")

    return summary
