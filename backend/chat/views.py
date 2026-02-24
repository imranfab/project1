import hashlib
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication

from authentication.models import CustomUser
from chat.models import (
    Conversation,
    Message,
    Version,
    Role,
    UploadedFile,
)
from chat.serializers import (
    ConversationSerializer,
    MessageSerializer,
    TitleSerializer,
    ConversationSummarySerializer,
    FileUploadSerializer,
    FileListSerializer,
)
from chat.utils.branching import make_branched_conversation


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return

def user_has_role(user, roles):
    if not user or not user.is_authenticated:
        return False

    if "admin" in roles and user.is_superuser:
        return True

    if "editor" in roles and user.is_staff:
        return True

    return False

# Chat basic endpoints

@api_view(["GET"])
@permission_classes([AllowAny])
def chat_root_view(request):
    return Response({"message": "Chat works!"})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_conversations(request):
    conversations = Conversation.objects.filter(
        deleted_at__isnull=True
    ).order_by("-modified_at")
    return Response(ConversationSerializer(conversations, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_conversations_branched(request):
    conversations = Conversation.objects.filter(
        deleted_at__isnull=True
    ).order_by("-modified_at")

    data = ConversationSerializer(conversations, many=True).data
    for c in data:
        make_branched_conversation(c)

    return Response(data)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_conversation_branched(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    data = ConversationSerializer(conversation).data
    make_branched_conversation(data)
    return Response(data)


@api_view(["POST"])
@permission_classes([AllowAny])
def add_conversation(request):
    if request.user.is_authenticated:
        user = request.user
    else:
        user, _ = CustomUser.objects.get_or_create(
            email="anonymous@soulpage.local",
            defaults={"is_active": True},
        )

    title = str(request.data.get("title", "New Chat"))[:100]
    conversation = Conversation.objects.create(title=title, user=user)
    version = Version.objects.create(conversation=conversation)

    messages = request.data.get("messages") or []
    for msg in messages:
        content = (msg.get("content") or "").strip()
        if not content:
            continue

        role_name = msg.get("role", "user")
        role, _ = Role.objects.get_or_create(name=str(role_name))

        Message.objects.create(
            content=content,
            role=role,
            version=version,
        )

    conversation.active_version = version
    conversation.save()

    return Response(
        ConversationSerializer(conversation).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def conversation_add_message(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)

    if not conversation.active_version:
        return Response(
            {"detail": "No active version"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = MessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(version=conversation.active_version)

    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def conversation_change_title(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    serializer = TitleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    conversation.title = serializer.validated_data["title"][:100]
    conversation.save()

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def conversation_soft_delete(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    conversation.deleted_at = timezone.now()
    conversation.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([AllowAny])
def conversation_manage(request, pk):
    return Response({"detail": "Not implemented"}, status=501)


@api_view(["POST"])
@permission_classes([AllowAny])
def conversation_add_version(request, pk):
    return Response({"detail": "Not implemented"}, status=501)


@api_view(["PUT"])
@permission_classes([AllowAny])
def conversation_switch_version(request, pk, version_id):
    return Response({"detail": "Not implemented"}, status=501)


@api_view(["POST"])
@permission_classes([AllowAny])
def version_add_message(request, pk):
    return Response({"detail": "Not implemented"}, status=501)

# Task 8: Conversation summaries
@api_view(["GET"])
@permission_classes([AllowAny])
def conversation_summaries(request):
    search = request.GET.get("search", "")
    page_number = request.GET.get("page", 1)
    page_size = int(request.GET.get("page_size", 10))

    queryset = Conversation.objects.filter(
        deleted_at__isnull=True
    ).filter(
        Q(title__icontains=search) | Q(summary__icontains=search)
    ).order_by("-modified_at")

    paginator = Paginator(queryset, page_size)
    page = paginator.get_page(page_number)

    serializer = ConversationSummarySerializer(page.object_list, many=True)
    return Response({
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page.number,
        "results": serializer.data,
    })

# Task 9–11: File upload RBAC

@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_file(request):
    if not user_has_role(request.user, ["admin", "editor"]):
        return Response(
            {"detail": "You do not have permission to upload files"},
            status=status.HTTP_403_FORBIDDEN,
        )

    file = request.FILES.get("file")
    if not file:
        return Response(
            {"detail": "File is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    hasher = hashlib.sha256()
    for chunk in file.chunks():
        hasher.update(chunk)
    file_hash = hasher.hexdigest()

    if UploadedFile.objects.filter(file_hash=file_hash).exists():
        return Response(
            {"detail": "File already uploaded"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    uploaded_file = UploadedFile.objects.create(
        file=file,
        filename=file.name,
        file_hash=file_hash,
        uploaded_by=request.user,
    )

    return Response(
        FileUploadSerializer(uploaded_file).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def list_uploaded_files(request):
    if not user_has_role(request.user, ["admin", "editor"]):
        return Response(
            {"detail": "You do not have permission to view files"},
            status=status.HTTP_403_FORBIDDEN,
        )

    files = UploadedFile.objects.all().order_by("-uploaded_at")
    serializer = FileListSerializer(files, many=True)
    return Response(serializer.data)


@api_view(["DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def delete_uploaded_file(request, pk):
    if not user_has_role(request.user, ["admin"]):
        return Response(
            {"detail": "Only admins can delete files"},
            status=status.HTTP_403_FORBIDDEN,
        )

    file_obj = get_object_or_404(UploadedFile, pk=pk)
    file_obj.delete()
    return Response({"message": "Deleted successfully"},
    status=status.HTTP_200_OK)
