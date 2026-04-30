from dataclasses import dataclass, field
from typing import List

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.db import transaction

from .models import Borrow, Reservation
from user_mgt.access import get_active_library_policy

@dataclass
class OverdueNotificationSummary:
    scanned: int = 0
    status_updated: int = 0
    emailed: int = 0
    skipped_missing_email: int = 0
    errors: List[str] = field(default_factory=list)

@dataclass
class ReservationNotificationSummary:
    material_id: str
    scanned: int = 0
    emailed: int = 0
    skipped_missing_email: int = 0
    errors: List[str] = field(default_factory=list)

def process_overdue_borrows_and_notify():
    """
    Main entry point for cron jobs to sync statuses and email users.
    """
    now = timezone.now()
    summary = OverdueNotificationSummary()

    # 1. First, sync the database status for all overdue items
    summary.status_updated = sync_overdue_borrow_statuses(now=now)

    # 2. Fetch those that need notification
    overdue_qs = Borrow.objects.select_related("member", "material").filter(
        status__in=["BORROWED", "OVERDUE"],
        due_date__lt=now,
        overdue_notified_at__isnull=True
    )
    
    summary.scanned = overdue_qs.count()

    for borrow in overdue_qs:
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

def sync_overdue_borrow_statuses(base_queryset=None, now=None):
    """
    Updates the database 'status' column to OVERDUE for items past their due date.
    """
    now = now or timezone.now()
    queryset = base_queryset if base_queryset is not None else Borrow.objects.all()
    
    overdue_qs = queryset.filter(
        status__in=["BORROWED", "OVERDUE"],
        due_date__lt=now,
    ).exclude(status="OVERDUE")
    
    return overdue_qs.update(status="OVERDUE")

def notify_reserved_members_material_available(material):
    """
    Notify active reservation holders that a material copy became available.
    """
    now = timezone.now()
    summary = ReservationNotificationSummary(material_id=str(material.pk))

    active_reservations = Reservation.objects.select_related("member", "material_id").filter(
        material_id=material,
        status="RESERVED",
        expiry_date__gt=now,
        availability_notified_at__isnull=True,
    ).order_by("reserve_date")

    summary.scanned = active_reservations.count()

    for reservation in active_reservations:
        member_email = (reservation.member.email or "").strip()
        if not member_email:
            summary.skipped_missing_email += 1
            continue

        member_name = (reservation.member.first_name or reservation.member.id_number).strip()
        subject = "Library Update: Reserved Material Is Available"
        message = (
            f"Dear {member_name},\n\n"
            f"The material you reserved, '{reservation.material_id.title}', is now available.\n"
            "Please visit the library promptly to borrow it.\n\n"
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
            summary.emailed += 1
        except Exception as exc:
            summary.errors.append(f"Reservation {reservation.id}: {exc}")

    return summary


def calculate_overdue_days(due_date, now=None, grace_period_days=0):
    """
    Return overdue days as full/partial day units once due_date has passed.
    Any delay beyond due_date counts as at least 1 overdue day.
    """
    now = now or timezone.now()
    if grace_period_days:
        due_date = due_date + timezone.timedelta(days=int(grace_period_days))
    if now <= due_date:
        return 0

    overdue_seconds = (now - due_date).total_seconds()
    return int((overdue_seconds + 86399) // 86400)


def get_borrow_policy(borrow):
    library = getattr(getattr(borrow, "material", None), "library", None) or getattr(getattr(borrow, "member", None), "library", None)
    return get_active_library_policy(library)


def finalize_return_for_borrow(borrow):
    """
    Mark borrow as returned and release one copy back to inventory atomically.
    Safe to call repeatedly; only applies changes when borrow is not RETURNED.
    """
    with transaction.atomic():
        locked_borrow = Borrow.objects.select_for_update().select_related("material").get(pk=borrow.pk)
        if locked_borrow.status == "RETURNED":
            return locked_borrow

        material = locked_borrow.material.__class__.objects.select_for_update().get(pk=locked_borrow.material.pk)
        material.available_copies = min(material.available_copies + 1, material.total_copies)
        material.save(update_fields=["available_copies"])

        locked_borrow.status = "RETURNED"
        locked_borrow.save(update_fields=["status"])

        transaction.on_commit(lambda: notify_reserved_members_material_available(material))
        return locked_borrow
