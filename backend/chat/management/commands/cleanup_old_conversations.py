from django.core.management.base import BaseCommand
from django.utils import timezone
from chat.models import Conversation
from datetime import timedelta

class Command(BaseCommand):
    help = 'Soft-deletes conversations older than 30 days'

    def handle(self, *args, **kwargs):
        days = 30
        cutoff_date = timezone.now() - timedelta(days=days)

        deleted_count = Conversation.objects.filter(
            created_at__lt=cutoff_date,
            deleted_at__isnull=True
        ).update(deleted_at=timezone.now())

        self.stdout.write(
            self.style.SUCCESS(f"{deleted_count} conversations soft-deleted.")
        )