"""
Task 3: Serializers for summary and file endpoints.
"""

from rest_framework import serializers

from .models import Conversation, Message, UploadedFile


class ConversationSummarySerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "summary",
            "summary_generated_at",
            "created_at",
            "modified_at",
            "message_count",
        ]
        read_only_fields = fields

    def get_message_count(self, obj) -> int:
        return Message.objects.filter(version__conversation=obj).count()


class UploadedFileSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = UploadedFile
        fields = [
            "id",
            "original_filename",
            "content_type",
            "size_bytes",
            "sha256",
            "uploaded_at",
            "uploaded_by",
        ]
        read_only_fields = fields


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        request = self.context["request"]
        sha256 = UploadedFile.compute_sha256(value)

        if UploadedFile.objects.filter(
            uploaded_by=request.user, sha256=sha256, is_deleted=False
        ).exists():
            raise serializers.ValidationError(
                "This file has already been uploaded. Duplicate uploads are not allowed."
            )

        value._sha256 = sha256
        return value
