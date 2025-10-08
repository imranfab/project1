from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Conversation



@receiver(post_save, sender=Conversation)
def generate_summary(sender, instance, created, **kwargs):
    if created and not instance.summary:
        # Generate a simple summary using the title or other fields
        summary_text = f"This conversation '{instance.title}' was created by user {instance.user.id}."
        instance.summary = summary_text
        instance.save()



# @receiver(pre_save, sender=Conversation)
# def generate_summary(sender, instance, **kwargs):
#     if not instance.summary:
#         print("instance summary 1111")
#         instance.summary = f"This conversation '{instance.title}' was created by user {instance.user.id}."
#     else:
#         print("instance summary 1111")