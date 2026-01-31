from celery import shared_task
from django.core.management import call_command

@shared_task
def cleanup_conversations_task():
    call_command('cleanup_conversations')
