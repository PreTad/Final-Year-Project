from django.core.management.base import BaseCommand

from transactions.services import process_overdue_borrows_and_notify


class Command(BaseCommand):
    help = "Mark overdue borrows and send one-time overdue reminder emails to members."

    def handle(self, *args, **options):
        summary = process_overdue_borrows_and_notify()

        self.stdout.write(
            self.style.SUCCESS(
                "Processed overdue borrows. "
                f"scanned={summary.scanned}, "
                f"status_updated={summary.status_updated}, "
                f"emailed={summary.emailed}, "
                f"skipped_missing_email={summary.skipped_missing_email}"
            )
        )

        for error in summary.errors:
            self.stderr.write(self.style.ERROR(error))
