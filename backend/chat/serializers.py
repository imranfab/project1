from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers

from chat.models import (
    Conversation,
    Message,
    Role,
    Version,
    UploadedFile,  
)

def should_serialize(validated_data, field_name) -> bool:
    if validated_data.get(field_name) is not None:
        return True
    return False

class TitleSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=True)


class VersionTimeIdSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()

class MessageSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Role.objects.all()
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "role",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "version"]

    def create(self, validated_data):
        # Creates a message instance in DB
        return Message.objects.create(**validated_data)

    def to_representation(self, instance):
        # Adds "versions" field for frontend compatibility
        representation = super().to_representation(instance)
        representation["versions"] = []
        return representation


class VersionSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True)
    active = serializers.SerializerMethodField()
    conversation_id = serializers.UUIDField(source="conversation.id")
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Version
        fields = [
            "id",
            "conversation_id",
            "root_message",
            "messages",
            "active",
            "created_at",
            "parent_version",
        ]
        read_only_fields = ["id", "conversation"]

    def get_active(self, obj):
        # Marks which version is currently active
        return obj == obj.conversation.active_version

    def get_created_at(self, obj):
        # Uses root message time if available
        if obj.root_message is None:
            return timezone.localtime(obj.conversation.created_at)
        return timezone.localtime(obj.root_message.created_at)

    def create(self, validated_data):
        messages_data = validated_data.pop("messages")
        version = Version.objects.create(**validated_data)

        for message_data in messages_data:
            Message.objects.create(version=version, **message_data)

        return version

    def update(self, instance, validated_data):
        instance.conversation = validated_data.get("conversation", instance.conversation)
        instance.parent_version = validated_data.get("parent_version", instance.parent_version)
        instance.root_message = validated_data.get("root_message", instance.root_message)

        # Ensure at least one updatable field is provided
        if not any(
            [
                should_serialize(validated_data, "conversation"),
                should_serialize(validated_data, "parent_version"),
                should_serialize(validated_data, "root_message"),
            ]
        ):
            raise ValidationError(
                "At least one field must be provided: "
                "conversation, parent_version, root_message"
            )

        instance.save()

        messages_data = validated_data.pop("messages", [])
        for message_data in messages_data:
            if "id" in message_data:
                # Update existing message
                message = Message.objects.get(id=message_data["id"], version=instance)
                message.content = message_data.get("content", message.content)
                message.role = message_data.get("role", message.role)
                message.save()
            else:
                # Create new message
                Message.objects.create(version=instance, **message_data)

        return instance


class ConversationSerializer(serializers.ModelSerializer):
    versions = VersionSerializer(many=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "summary",       
            "active_version",
            "versions",
            "modified_at",
        ]

    def create(self, validated_data):
        versions_data = validated_data.pop("versions", [])
        conversation = Conversation.objects.create(**validated_data)

        for version_data in versions_data:
            serializer = VersionSerializer(data=version_data)
            if serializer.is_valid():
                serializer.save(conversation=conversation)

        return conversation

    def update(self, instance, validated_data):
        instance.title = validated_data.get("title", instance.title)

        active_version_id = validated_data.get(
            "active_version", instance.active_version
        )
        if active_version_id is not None:
            instance.active_version = Version.objects.get(id=active_version_id)

        instance.save()

        versions_data = validated_data.pop("versions", [])
        for version_data in versions_data:
            if "id" in version_data:
                version = Version.objects.get(id=version_data["id"], conversation=instance)
                serializer = VersionSerializer(version, data=version_data)
            else:
                serializer = VersionSerializer(data=version_data)

            if serializer.is_valid():
                serializer.save(conversation=instance)

        return instance

class ConversationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "summary",
            "created_at",
        ]



class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = [
            "id",
            "file",
            "filename",
            "uploaded_at",
        ]
        read_only_fields = ["id", "filename", "uploaded_at"]


class FileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = [
            "id",
            "filename",
            "file",
            "uploaded_at",
        ]
