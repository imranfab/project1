from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Conversation, Message

def _build_summary(conv: Conversation, limit_words: int = 40) -> str:
    msgs = Message.objects.filter(version__conversation=conv).order_by("created_at").values_list("content", flat=True)[:5]
    text = " ".join([m for m in msgs if m])
    words = text.split()
    return " ".join(words[:limit_words])

@receiver(post_save, sender=Message)
def update_conversation_summary(sender, instance: Message, created, **kwargs):
    if not created:
        return
    conv = instance.version.conversation
    new_summary = _build_summary(conv)
    if new_summary and new_summary != conv.summary:
        conv.summary = new_summary
        conv.save(update_fields=["summary"])
