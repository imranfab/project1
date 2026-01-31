from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from chat.models import Conversation

class Command(BaseCommand):
    help = "Delete conversations older than 30 days"

    def handle(self, *args, **kwargs):
        cutoff_date = timezone.now() - timedelta(days=30)
        old_conversations = Conversation.objects.filter(
            created_at__lt=cutoff_date
        )

        count = old_conversations.count()
        old_conversations.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} old conversations"
            )
        )
