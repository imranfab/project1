# chat/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Conversation, Message
import openai

@receiver(post_save, sender=Conversation)
def generate_summary(sender, instance, created, **kwargs):
    if created or not instance.summary:
        messages = Message.objects.filter(conversation=instance).order_by('created_at')
        # new one
        # messages = Message.objects.filter(version__conversation=instance).order_by('created_at')

        text = "\n".join([msg.content for msg in messages])

        if text.strip():
            try:
                # Use OpenAI or a simple logic to summarize
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Summarize this conversation briefly."},
                        {"role": "user", "content": text[:3000]}  # avoid token limit
                    ]
                )
                summary = response.choices[0].message.content.strip()
            except Exception as e:
                summary = "Summary generation failed."

            instance.summary = summary
            instance.save(update_fields=["summary"])