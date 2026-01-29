from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message


def generate_summary(text, max_length=200):
    if not text:
        return ""
    return text[:max_length] + ("..." if len(text) > max_length else "")


@receiver(post_save, sender=Message)
def create_conversation_summary(sender, instance, created, **kwargs):
    conversation = instance.version.conversation

    # Do nothing if summary already exists
    if conversation.summary:
        return

    # Get messages of this conversation (ordered by created_at)
    messages = Message.objects.filter(
        version__conversation=conversation
    ).order_by("created_at")

    if not messages.exists():
        return

    # Combine message contents (you can limit to first N messages)
    combined_text = " ".join(m.content for m in messages[:3])

    conversation.summary = generate_summary(combined_text)
    conversation.save(update_fields=["summary"])
