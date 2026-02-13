from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination  
from chat.models import Conversation, Message, Role, Version,UploadedFile


def should_serialize(validated_data, field_name) -> bool:
    if validated_data.get(field_name) is not None:
        return True


class TitleSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=True)


class VersionTimeIdSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()


class MessageSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(slug_field="name", queryset=Role.objects.all())

    class Meta:
        model = Message
        fields = [
            "id",  # DB
            "content",
            "role",  # required
            "created_at",  # DB, read-only
        ]
        read_only_fields = ["id", "created_at", "version"]

    def create(self, validated_data):
        message = Message.objects.create(**validated_data)
        return message

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["versions"] = []  # add versions field
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
            "conversation_id",  # DB
            "root_message",
            "messages",
            "active",
            "created_at",  # DB, read-only
            "parent_version",  # optional
        ]
        read_only_fields = ["id", "conversation"]

    @staticmethod
    def get_active(obj):
        return obj == obj.conversation.active_version

    @staticmethod
    def get_created_at(obj):
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
        if not any(
            [
                should_serialize(validated_data, "conversation"),
                should_serialize(validated_data, "parent_version"),
                should_serialize(validated_data, "root_message"),
            ]
        ):
            raise ValidationError(
                "At least one of the following fields must be provided: conversation, parent_version, root_message"
            )
        instance.save()

        messages_data = validated_data.pop("messages", [])
        for message_data in messages_data:
            if "id" in message_data:
                message = Message.objects.get(id=message_data["id"], version=instance)
                message.content = message_data.get("content", message.content)
                message.role = message_data.get("role", message.role)
                message.save()
            else:
                Message.objects.create(version=instance, **message_data)

        return instance


class ConversationSerializer(serializers.ModelSerializer):
    versions = VersionSerializer(many=True)

    class Meta:
        model = Conversation
        fields = [
            "id",  # DB
            "title",  # required
            "active_version",
            "versions",  # optional
            "modified_at",  # DB, read-only
        ]

    def create(self, validated_data):
        versions_data = validated_data.pop("versions", [])
        conversation = Conversation.objects.create(**validated_data)
        for version_data in versions_data:
            version_serializer = VersionSerializer(data=version_data)
            if version_serializer.is_valid():
                version_serializer.save(conversation=conversation)

        return conversation

    def update(self, instance, validated_data):
        instance.title = validated_data.get("title", instance.title)
        active_version_id = validated_data.get("active_version", instance.active_version)
        if active_version_id is not None:
            active_version = Version.objects.get(id=active_version_id)
            instance.active_version = active_version
        instance.save()

        versions_data = validated_data.pop("versions", [])
        for version_data in versions_data:
            if "id" in version_data:
                version = Version.objects.get(id=version_data["id"], conversation=instance)
                version_serializer = VersionSerializer(version, data=version_data)
            else:
                version_serializer = VersionSerializer(data=version_data)
            if version_serializer.is_valid():
                version_serializer.save(conversation=instance)

        return instance


class ConversationSummarySerializer(serializers.ModelSerializer):
    """Serializer specifically for conversation summaries endpoint"""
    version_count = serializers.IntegerField(read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'summary', 'created_at', 'modified_at', 'version_count', 'message_count', 'user']
        read_only_fields = ['id', 'created_at', 'modified_at', 'summary']
    
    def get_message_count(self, obj):
        """Get total message count in active version"""
        if obj.active_version:
            return obj.active_version.messages.count()
        return 0

class TitleSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=True)


class UploadedFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    uploaded_by = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UploadedFile
        fields = [
            'id', 
            'file', 
            'file_url',
            'original_filename', 
            'file_size', 
            'file_type', 
            'file_hash', 
            'uploaded_at',
            'uploaded_by',
            'user'
        ]
        read_only_fields = ['id', 'file_hash', 'file_size', 'file_type', 'uploaded_at', 'file_url', 'uploaded_by']
    
    def get_file_url(self, obj):
        """Get the full URL of the uploaded file"""
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None
    
    def validate_file(self, value):
        """Validate file upload"""
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(f"File size exceeds maximum allowed size of {max_size / (1024*1024)}MB")
        
        return value
    
    def create(self, validated_data):
        """Override create to handle duplicate file check"""
        file = validated_data.get('file')
        user = validated_data.get('user')
        
        # Calculate file hash
        file_hash = UploadedFile.calculate_file_hash(file)
        
        # Check if file with same hash already exists for this user
        existing_file = UploadedFile.objects.filter(file_hash=file_hash, user=user).first()
        
        if existing_file:
            raise serializers.ValidationError({
                'file': 'This file has already been uploaded.',
                'existing_file_id': str(existing_file.id),
                'existing_file_name': existing_file.original_filename,
                'uploaded_at': existing_file.uploaded_at
            })
        
        # Set file metadata
        validated_data['file_hash'] = file_hash
        validated_data['file_size'] = file.size
        validated_data['file_type'] = file.content_type or 'application/octet-stream'
        validated_data['original_filename'] = file.name
        
        return super().create(validated_data)


# Pagination class for summaries
class SummaryPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100