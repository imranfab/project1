"""
Task 1: Auto-trigger summary generation after an assistant message is saved.
"""

import logging
import threading

logger = logging.getLogger("chat.signals")


def connect_signals():
    from django.db.models.signals import post_save
    from django.dispatch import receiver
    from .models import Message

    @receiver(post_save, sender=Message, dispatch_uid="auto_summary_on_message")
    def auto_generate_summary(sender, instance, created, **kwargs):
        if not created:
            return
        # Only trigger after assistant messages
        if instance.role.name.lower() != "assistant":
            return

        conversation = instance.version.conversation

        def run():
            from .summary import generate_summary
            try:
                generate_summary(conversation)
            except Exception as exc:
                logger.error("Async summary failed for %s: %s", conversation.pk, exc)

        threading.Thread(target=run, daemon=True).start()
        logger.debug("Triggered summary for conversation %s", conversation.pk)
