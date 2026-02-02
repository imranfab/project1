import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from chat.models import Conversation

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Clean up old or deleted conversations"

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=0)

        deleted_qs = Conversation.objects.filter(deleted_at__isnull=False)
        old_qs = Conversation.objects.filter(created_at__lt=cutoff)

        deleted_count = deleted_qs.count()
        old_count = old_qs.count()

        deleted_qs.delete()
        old_qs.delete()

        logger.info(
            f"[CRON] Cleanup ran: {deleted_count} deleted, {old_count} old removed"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup ran: {deleted_count} deleted, {old_count} old"
            )
        )
