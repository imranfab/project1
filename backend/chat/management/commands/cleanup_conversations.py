from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from chat.models import Conversation


class Command(BaseCommand):
    help = "Soft delete conversations older than given number of days"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete conversations older than this many days",
        )

    def handle(self, *args, **options):
        days = options["days"]
        cutoff_date = timezone.now() - timedelta(days=days)

        conversations = Conversation.objects.filter(
            modified_at__lt=cutoff_date,
            deleted_at__isnull=True,
        )

        count = conversations.count()

        for convo in conversations:
            convo.deleted_at = timezone.now()
            convo.save(update_fields=["deleted_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Soft-deleted {count} conversation(s) older than {days} days"
            )
        )
