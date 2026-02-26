import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from chat.models import Conversation

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Clean up old or deleted conversations"

    def handle(self, *args, **options):
      
        cutoff = timezone.now() - timedelta(minutes=1)

        qs = (
            Conversation.objects.filter(deleted_at__isnull=False) |
            Conversation.objects.filter(created_at__lt=cutoff)
        )

        total = qs.count()

        with open("/tmp/cleanup_test.log", "a") as f:
            f.write(f"CRON RAN — matched={total} at {timezone.now()}\n")

        deleted, _ = qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup ran: {deleted} deleted (matched {total})"
            )
        )

        logger.info(
            f"[CRON] Cleanup ran: {deleted} deleted (matched {total})"
        )
