"""
Task 1: Backfill summaries for conversations missing one.

Usage:
    python manage.py generate_summaries
    python manage.py generate_summaries --limit 50
"""

import time
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger("chat.management")


class Command(BaseCommand):
    help = "Generate summaries for conversations that don't have one yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=100,
            help="Max conversations to process (default: 100).",
        )
        parser.add_argument(
            "--delay", type=float, default=0.5,
            help="Seconds to wait between API calls (default: 0.5).",
        )

    def handle(self, *args, **options):
        from chat.models import Conversation
        from chat.summary import generate_summary

        qs = Conversation.objects.filter(summary="", deleted_at__isnull=True)[:options["limit"]]
        total = qs.count()
        self.stdout.write(f"Processing {total} conversation(s)...")

        success = 0
        for conv in qs:
            result = generate_summary(conv)
            if result:
                success += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ {conv.title}"))
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠ {conv.title} — skipped"))
            time.sleep(options["delay"])

        self.stdout.write(self.style.SUCCESS(f"Done. {success}/{total} summaries generated."))
