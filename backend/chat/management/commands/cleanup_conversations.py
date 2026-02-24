"""
Task 2: Delete conversations older than N days.

Usage:
    python manage.py cleanup_conversations
    python manage.py cleanup_conversations --days 60
    python manage.py cleanup_conversations --days 90 --dry-run
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

logger = logging.getLogger("chat.management")


class Command(BaseCommand):
    help = "Delete conversations last modified more than N days ago."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=90,
            help="Delete conversations older than this many days (default: 90).",
        )
        parser.add_argument(
            "--dry-run", action="store_true", default=False,
            help="Show how many would be deleted without actually deleting.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]

        if days < 1:
            raise CommandError("--days must be a positive integer.")

        from chat.models import Conversation

        cutoff = timezone.now() - timedelta(days=days)
        qs = Conversation.objects.filter(modified_at__lt=cutoff)
        count = qs.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] Would delete {count} conversation(s) older than {days} days."
            ))
            return

        qs.delete()
        msg = f"Deleted {count} conversation(s) older than {days} days."
        self.stdout.write(self.style.SUCCESS(msg))
        logger.info(msg)
