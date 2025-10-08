import os
import io
import logging
activity_log = logging.getLogger("activity")  # <- updated logger name

from django.core.cache import cache
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from rest_framework.permissions import BasePermission
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import generics, filters, pagination
from rest_framework.permissions import IsAuthenticated

from chat.models import Conversation, Message, Version, UploadedFile
from chat.serializers import ConversationSerializer, MessageSerializer, TitleSerializer, VersionSerializer, UploadedFileSerializer
from chat.utils.branching import make_branched_conversation


@api_view(["GET"])
def chat_root_view(request):
    return Response({"message": "Chat works!"}, status=status.HTTP_200_OK)


@login_required
@api_view(["GET"])
def get_conversations(request):
    conversations = Conversation.objects.filter(user=request.user, deleted_at__isnull=True).order_by("-modified_at")
    serializer = ConversationSerializer(conversations, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@login_required
@api_view(["GET"])
def get_conversations_branched(request):
    conversations = Conversation.objects.filter(user=request.user, deleted_at__isnull=True).order_by("-modified_at")
    conversations_serializer = ConversationSerializer(conversations, many=True)
    conversations_data = conversations_serializer.data

    for conversation_data in conversations_data:
        make_branched_conversation(conversation_data)

    return Response(conversations_data, status=status.HTTP_200_OK)


@login_required
@api_view(["GET"])
def get_conversation_branched(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response({"detail": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

    conversation_serializer = ConversationSerializer(conversation)
    conversation_data = conversation_serializer.data
    make_branched_conversation(conversation_data)

    return Response(conversation_data, status=status.HTTP_200_OK)


@login_required
@api_view(["POST"])
def add_conversation(request):
    try:
        conversation_data = {"title": request.data.get("title", "Mock title"), "user": request.user}
        conversation = Conversation.objects.create(**conversation_data)
        version = Version.objects.create(conversation=conversation)

        messages_data = request.data.get("messages", [])
        for idx, message_data in enumerate(messages_data):
            message_serializer = MessageSerializer(data=message_data)
            if message_serializer.is_valid():
                message_serializer.save(version=version)
                if idx == 0:
                    version.save()
            else:
                return Response(message_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        conversation.active_version = version
        conversation.save()

        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@login_required
@api_view(["GET", "PUT", "DELETE"])
def conversation_manage(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data)

    elif request.method == "PUT":
        serializer = ConversationSerializer(conversation, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@login_required
@api_view(["PUT"])
def conversation_change_title(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = TitleSerializer(data=request.data)

    if serializer.is_valid():
        conversation.title = serializer.data.get("title")
        conversation.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response({"detail": "Title not provided"}, status=status.HTTP_400_BAD_REQUEST)


@login_required
@api_view(["PUT"])
def conversation_soft_delete(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    conversation.deleted_at = timezone.now()
    conversation.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


@login_required
@api_view(["POST"])
def conversation_add_message(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
        version = conversation.active_version
    except Conversation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if version is None:
        return Response({"detail": "Active version not set for this conversation."}, status=status.HTTP_400_BAD_REQUEST)

    serializer = MessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(version=version)
        return Response(
            {
                "message": serializer.data,
                "conversation_id": conversation.id,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required
@api_view(["POST"])
def conversation_add_version(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
        version = conversation.active_version
        root_message_id = request.data.get("root_message_id")
        root_message = Message.objects.get(pk=root_message_id)
    except Conversation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    except Message.DoesNotExist:
        return Response({"detail": "Root message not found"}, status=status.HTTP_404_NOT_FOUND)

    if root_message.version.conversation != conversation:
        return Response({"detail": "Root message not part of the conversation"}, status=status.HTTP_400_BAD_REQUEST)

    new_version = Version.objects.create(
        conversation=conversation, parent_version=root_message.version, root_message=root_message
    )

    messages_before_root = Message.objects.filter(version=version, created_at__lt=root_message.created_at)
    new_messages = [
        Message(content=message.content, role=message.role, version=new_version) for message in messages_before_root
    ]
    Message.objects.bulk_create(new_messages)

    conversation.active_version = new_version
    conversation.save()

    serializer = VersionSerializer(new_version)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@login_required
@api_view(["PUT"])
def conversation_switch_version(request, pk, version_id):
    try:
        conversation = Conversation.objects.get(pk=pk)
        version = Version.objects.get(pk=version_id, conversation=conversation)
    except Conversation.DoesNotExist:
        return Response({"detail": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
    except Version.DoesNotExist:
        return Response({"detail": "Version not found"}, status=status.HTTP_404_NOT_FOUND)

    conversation.active_version = version
    conversation.save()

    return Response(status=status.HTTP_204_NO_CONTENT)


@login_required
@api_view(["POST"])
def version_add_message(request, pk):
    try:
        version = Version.objects.get(pk=pk)
    except Version.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = MessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(version=version)
        return Response(
            {
                "message": serializer.data,
                "version_id": version.id,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rag_query(request):
    query = (request.data.get("query") or "").strip()
    top_k = int(request.data.get("top_k") or 3)
    if not query:
        return Response({"detail": "Query is required"}, status=400)

    qs = UploadedFile.objects.filter(user=request.user)\
         .exclude(extracted_text__isnull=True).exclude(extracted_text="")

    hits = []
    for uf in qs:
        text = uf.extracted_text or ""
        pos = text.lower().find(query.lower())
        if pos != -1:
            start = max(0, pos - 200)
            end = min(len(text), pos + 200)
            hits.append({
                "file_id": str(uf.id),
                "file": uf.file.name,
                "snippet": text[start:end],
            })
    return Response({"query": query, "results": hits[:top_k]}, status=200)


class IsUploaderRole(BasePermission):
    allowed_groups = {"uploader", "admin"}

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        user_groups = set(g.lower() for g in user.groups.values_list("name", flat=True))
        return bool(self.allowed_groups & user_groups)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUploaderRole])
def process_file(request, pk):
    try:
        uf = UploadedFile.objects.get(pk=pk, user=request.user)
    except UploadedFile.DoesNotExist:
        return Response({"detail": "Not found"}, status=404)

    name = uf.file.name.lower()
    if name.endswith(".txt"):
        uf.extracted_text = uf.file.read().decode("utf-8", errors="ignore")
    else:
        uf.extracted_text = "(processing not implemented for this file type)"
    activity_log.info(
        f'process user="{request.user.id}" email="{request.user.email}" '
        f'file="{uf.file.name}" id="{uf.id}" type="{"txt" if name.endswith(".txt") else "other"}"'
    )
    uf.save()
    return Response({"id": str(uf.id), "extracted": bool(uf.extracted_text)}, status=200)


class ConversationPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class ConversationSummaryView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    pagination_class = ConversationPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "summary"]
    ordering_fields = ["created_at", "modified_at", "title"]
    ordering = ["-modified_at"]

    def get_queryset(self):
        queryset = Conversation.objects.filter(user=self.request.user, deleted_at__isnull=True)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        return queryset

    def list(self, request, *args, **kwargs):
        cache_key = f"summaries:{request.user.id}:{request.get_full_path()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=200)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=300)  # 5 minutes
        return response


class FileUploadView(generics.CreateAPIView):
    serializer_class = UploadedFileSerializer
    parser_classes = [FormParser, MultiPartParser]
    permission_classes = [IsAuthenticated, IsUploaderRole]

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        activity_log.info(
            f'upload user="{self.request.user.id}" email="{self.request.user.email}" '
            f'file="{instance.file.name}" id="{instance.id}" checksum="{instance.checksum}"'
        )


class FileListView(generics.ListAPIView):
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated, IsUploaderRole]

    def get_queryset(self):
        activity_log.info(f'list user="{self.request.user.id}" email="{self.request.user.email}"')
        return UploadedFile.objects.filter(user=self.request.user).order_by("-uploaded_at")


class FileDeleteView(generics.DestroyAPIView):
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated, IsUploaderRole]

    def get_queryset(self):
        return UploadedFile.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        activity_log.info(
            f'delete user="{self.request.user.id}" email="{self.request.user.email}" '
            f'file="{instance.file.name}" id="{instance.id}"'
        )
        if instance.file and default_storage.exists(instance.file.name):
            default_storage.delete(instance.file.name)
        instance.delete()
