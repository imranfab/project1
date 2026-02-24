"""
Task 1: Generate and store a conversation summary using OpenAI.
Called automatically via signal after every assistant message.
"""

import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("chat.summary")


def _build_transcript(conversation) -> str:
    """Get all messages from the active version as plain text."""
    from .models import Message

    version = conversation.active_version
    if not version:
        version = conversation.versions.order_by("-root_message__created_at").first()
    if not version:
        return ""

    lines = []
    for msg in Message.objects.filter(version=version).order_by("created_at"):
        lines.append(f"{msg.role.name.capitalize()}: {msg.content}")
    return "\n".join(lines)


def generate_summary(conversation) -> str:
    """
    Generate a summary for the conversation and save it.
    Returns the summary string, or empty string on failure.
    """
    transcript = _build_transcript(conversation)
    if not transcript:
        return ""

    try:
        import openai
        openai.api_type = getattr(settings, "OPENAI_API_TYPE", "openai")
        openai.api_base = getattr(settings, "OPENAI_API_BASE", None)
        openai.api_version = getattr(settings, "OPENAI_API_VERSION", None)
        openai.api_key = settings.OPENAI_API_KEY

        response = openai.ChatCompletion.create(
            engine=getattr(settings, "OPENAI_SUMMARY_ENGINE", "gpt-35-turbo"),
            messages=[
                {
                    "role": "system",
                    "content": "Summarise the following conversation in 2-3 sentences.",
                },
                {"role": "user", "content": transcript[:3000]},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        summary_text = response["choices"][0]["message"]["content"].strip()

    except Exception as exc:
        logger.error("Summary generation failed for conversation %s: %s", conversation.pk, exc)
        return ""

    conversation.summary = summary_text
    conversation.summary_generated_at = timezone.now()
    conversation.save(update_fields=["summary", "summary_generated_at"])
    logger.info("Summary saved for conversation %s", conversation.pk)
    return summary_text
