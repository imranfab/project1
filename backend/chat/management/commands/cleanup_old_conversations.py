import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from chat.models import History 

class Command(BaseCommand):

    #Deletes conversations older than 30 days from SQLite.

    def handle(self, *args, **options):
        threshold = timezone.now() - datetime.timedelta(days=30)

        old_conversations = History.objects.filter(timestamp=threshold)
        count = old_conversations.count()
        
        # Delete the old conversations
        old_conversations.delete()
        
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} conversations older than 30 days."))
