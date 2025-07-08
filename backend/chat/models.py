import uuid

from django.db import models

from authentication.models import CustomUser
# task-3
import hashlib
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import hashlib
from django.contrib.auth.models import User


class Role(models.Model):
    name = models.CharField(max_length=20, blank=False, null=False, default="user")

    def __str__(self):
        return self.name


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, blank=False, null=False, default="Mock title")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    active_version = models.ForeignKey(
        "Version", null=True, blank=True, on_delete=models.CASCADE, related_name="current_version_conversations"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    def version_count(self):
        return self.versions.count()

    version_count.short_description = "Number of versions"


# task-3 file uploadwith duplicate check
User = get_user_model()

class FileUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_hash = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'file_hash'], name='unique_user_file_hash')
        ]

    def clean(self):
        # Check for duplicate files for the same user
        if FileUpload.objects.filter(user=self.user, file_hash=self.file_hash).exclude(pk=self.pk).exists():
            raise ValidationError("Duplicate file. Already uploaded by this user.")

    def save(self, *args, **kwargs):
        # Only calculate hash if not already set
        if not self.file_hash:
            hasher = hashlib.sha256()
            for chunk in self.file.chunks():
                hasher.update(chunk)
            self.file_hash = hasher.hexdigest()

        # Set file name and size automatically
        self.file_name = self.file.name
        self.file_size = self.file.size

        # Run validation and save
        self.full_clean()  # Calls clean()
        super().save(*args, **kwargs)

    def _str_(self):
        return f"{self.user.email} - {self.file_name}"



class Version(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey("Conversation", related_name="versions", on_delete=models.CASCADE)
    parent_version = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    root_message = models.ForeignKey(
        "Message", null=True, blank=True, on_delete=models.SET_NULL, related_name="root_message_versions"
    )

    def __str__(self):
        if self.root_message:
            return f"Version of `{self.conversation.title}` created at `{self.root_message.created_at}`"
        else:
            return f"Version of `{self.conversation.title}` with no root message yet"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.TextField(blank=False, null=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.ForeignKey("Version", related_name="messages", on_delete=models.CASCADE)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.version.conversation.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."
    
class FileLog(models.Model):
    ACTION_CHOICES= [
    ('UPLOAD', 'Upload'),
    ('DELETE', 'Delete'),
    ('ACCESS', 'Access'),
]
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    file_name = models.CharField(max_length=255)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"{self.timestamp} - {self.user} - {self.action} - {self.file_name}"




    