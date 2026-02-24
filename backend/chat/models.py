import uuid

from django.db import models
from django.utils import timezone

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

    # --- Task 1: new summary fields ---
    summary = models.TextField(
        blank=True,
        default="",
        help_text="Auto-generated summary of the conversation.",
    )
    summary_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the summary was last generated.",
    )

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
        self.version.conversation.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."


# --- Task 3: File upload model ---

def upload_to(instance, filename):
    return f"uploads/{instance.uploaded_by_id}/{filename}"


class UploadedFile(models.Model):
    uploaded_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="uploaded_files"
    )
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to=upload_to)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64, help_text="SHA-256 hash for deduplication.")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        unique_together = [("uploaded_by", "sha256")]

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    @staticmethod
    def compute_sha256(file_obj) -> str:
        import hashlib
        h = hashlib.sha256()
        for chunk in file_obj.chunks():
            h.update(chunk)
        file_obj.seek(0)
        return h.hexdigest()

    def __str__(self):
        return self.original_filename


# --- Task 4: Audit log ---

class FileAccessLog(models.Model):
    ACTION_UPLOAD = "upload"
    ACTION_DELETE = "delete"
    ACTION_LIST = "list"
    ACTION_CHOICES = [
        (ACTION_UPLOAD, "Upload"),
        (ACTION_DELETE, "Delete"),
        (ACTION_LIST, "List"),
    ]

    file = models.ForeignKey(
        UploadedFile, on_delete=models.SET_NULL, null=True, blank=True, related_name="access_logs"
    )
    performed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, related_name="file_actions"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.performed_by} {self.action} @ {self.timestamp}"
