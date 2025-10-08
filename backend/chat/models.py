import uuid
import io
from django.db import models

from authentication.models import CustomUser


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
    status = models.CharField(max_length=20, blank=False, null=False, default="active")
    summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    def version_count(self):
        return self.versions.count()

    version_count.short_description = "Number of versions"


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
        super().save(*args, **kwargs)

        messages = self.version.messages.all()
        summary_text = "".join([message.content for message in messages])[:200]
        self.version.conversation.summary = summary_text
        self.version.conversation.save()

    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."



import hashlib
from django.core.exceptions import ValidationError


class UploadedFile(models.Model):
    """
    Model to store uploaded files with a checksum for duplication check.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    checksum = models.CharField(max_length=64, unique=True)
    extracted_text = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.file.name}"

    def clean(self):
        # Calculate checksum for duplication validation
        if self.file:
            sha = hashlib.sha256()
            for chunk in self.file.chunks():
                sha.update(chunk)
            checksum = sha.hexdigest()
            if UploadedFile.objects.filter(checksum=checksum).exists():
                raise ValidationError("This file already exists.")
            self.checksum = checksum

    def save(self, *args, **kwargs):
        if not self.checksum and self.file:
            sha = hashlib.sha256()
            for chunk in self.file.chunks():
                sha.update(chunk)
            self.checksum = sha.hexdigest()
        super().save(*args, **kwargs)

