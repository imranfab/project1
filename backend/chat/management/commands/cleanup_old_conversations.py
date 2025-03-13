from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from backend.chat.models import Conversation  # Import your Conversation model

class Command(BaseCommand):
    help = 'Clean up old conversations that haven\'t been modified in the last 6 months.'

    def handle(self, *args, **kwargs):
        # Define the cutoff date (6 months ago)
        six_months_ago = timezone.now() - timedelta(days=6*30)  # Approx 6 months

        # Query conversations that haven't been modified since the cutoff date
        old_conversations = Conversation.objects.filter(modified_at__lte=six_months_ago, deleted_at__isnull=True)

        # If there are old conversations, delete them
        if old_conversations.exists():
            # You can choose to soft delete or hard delete. Here we are hard deleting.
            old_conversations.delete()

            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {old_conversations.count()} old conversations.'))
        else:
            self.stdout.write(self.style.SUCCESS('No old conversations found to delete.'))
