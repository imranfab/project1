import uuid
import os
from django.db import models
import hashlib
import mimetypes
from authentication.models import CustomUser
from django.core.exceptions import ValidationError


class Role(models.Model):
    name = models.CharField(max_length=20, blank=False, null=False, default="user")

    def __str__(self):
        return self.name


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, blank=False, null=False, default="Mock title")
    summary = models.TextField(blank=True, null=True)  # Added NEW FIELD SUMMARY
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    active_version = models.ForeignKey(
        "Version", null=True, blank=True, on_delete=models.CASCADE, related_name="current_version_conversations"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

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
        print(" Message.save() called")
        
        # Save the message first
        super().save(*args, **kwargs)

        conversation = self.version.conversation
        print("Conversation ID:", conversation.id)

        # Ensure active_version is set
        if not conversation.active_version:
            conversation.active_version = self.version
            print(" active_version set")

        # Get all messages from the active version
        messages = conversation.active_version.messages.all()
        message_texts = [f"{m.role.name}: {m.content}" for m in messages]

        print("Messages count:", len(message_texts))

        # Generate summary if there are messages
        if message_texts:
            try:
                from chat.utils.openai_summary import generate_conversation_summary
                summary = generate_conversation_summary(message_texts)
                print(" Summary generated:", summary)

                conversation.summary = summary
                conversation.save(update_fields=["summary", "active_version"])
                print(" Summary saved")

            except Exception as e:
                print(" OpenAI error:", e)
        else:
            print(" No messages found")

    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."

# NEW MODEL FOR FILE UPLOADS
class UploadedFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="uploaded_files")
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=100)
    file_hash = models.CharField(max_length=64, unique=True, help_text="SHA-256 hash for duplicate detection")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['file_hash']),
            models.Index(fields=['user', '-uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} - {self.user.get_username()}"

    # @staticmethod
    # def calculate_file_hash(file):
    #     """Calculate SHA-256 hash of file content"""
    #     sha256_hash = hashlib.sha256()
        
    #     # Reset file pointer to beginning
    #     file.seek(0)
        
    #     # Read file in chunks to handle large files
    #     for chunk in file.chunks():
    #         sha256_hash.update(chunk)
        
    #     # Reset file pointer again
    #     file.seek(0)
        
    #     return sha256_hash.hexdigest()
    
    # def save(self, *args, **kwargs):
    #     """Override save to calculate file hash before saving"""
    #     if not self.file_hash and self.file:
    #         self.file_hash = self.calculate_file_hash(self.file)
        
    #     if not self.file_size and self.file:
    #         self.file_size = self.file.size
        
    #     if not self.file_type and self.file:
    #         mime_type, _ = mimetypes.guess_type(self.file.name)
    #         self.file_type = mime_type or "application/octet-stream"
        
    #     if not self.original_filename and self.file:
    #         self.original_filename = self.file.name
        
    #     super().save(*args, **kwargs)
    
    
    @staticmethod
    def calculate_file_hash(file):
        sha256_hash = hashlib.sha256()
        file.seek(0)
        for chunk in file.chunks():
            sha256_hash.update(chunk)
        file.seek(0)
        return sha256_hash.hexdigest()

    def clean(self):
        if self.file:
            file_hash = self.calculate_file_hash(self.file)
            if UploadedFile.objects.filter(file_hash=file_hash).exists():
                raise ValidationError(
                    {"file": "This file already exists (duplicate upload)."}
                )

    def save(self, *args, **kwargs):
        if self.file and not self.file_hash:
            self.file_hash = self.calculate_file_hash(self.file)

        if self.file and not self.file_size:
            self.file_size = self.file.size

        if self.file and not self.file_type:
            mime_type, _ = mimetypes.guess_type(self.file.name)
            self.file_type = mime_type or "application/octet-stream"

        if self.file and not self.original_filename:
            self.original_filename = self.file.name

        super().save(*args, **kwargs)
        
    def delete(self, *args, **kwargs):
        """Override delete to also delete the physical file"""
        # Delete the physical file
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        
        super().delete(*args, **kwargs)
