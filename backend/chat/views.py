import hashlib
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from authentication.models import CustomUser
from chat.models import (
    Conversation,
    Message,
    Version,
    Role,
    UploadedFile,   #  (Task 3)
)
from chat.serializers import (
    ConversationSerializer,
    MessageSerializer,
    TitleSerializer,
    ConversationSummarySerializer,  # (Task 3)
    FileUploadSerializer,            #  (Task 3)
    FileListSerializer,              # (Task 3)
)
from chat.utils.branching import make_branched_conversation


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

    return Response(
        ConversationSerializer(conversations, many=True).data
    )


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
    try:
        conversation = Conversation.objects.get(pk=pk)
    except Conversation.DoesNotExist:
        return Response(
            {"detail": "Not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    data = ConversationSerializer(conversation).data
    make_branched_conversation(data)

    return Response(data)



@api_view(["POST"])
@permission_classes([AllowAny])
def add_conversation(request):
    # Ensure valid user
    if request.user.is_authenticated:
        user = request.user
    else:
        user, _ = CustomUser.objects.get_or_create(
            email="anonymous@soulpage.local",
            defaults={"is_active": True},
        )

    # Protect title length
    raw_title = request.data.get("title", "New Chat")
    title = raw_title[:100]

    conversation = Conversation.objects.create(
        title=title,
        user=user,
    )

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
    try:
        conversation = Conversation.objects.get(pk=pk)
        version = conversation.active_version
    except Conversation.DoesNotExist:
        return Response(
            {"detail": "Not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = MessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(version=version)

    return Response(
        serializer.data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def conversation_change_title(request, pk):
    try:
        conversation = Conversation.objects.get(pk=pk)
    except Conversation.DoesNotExist:
        return Response(
            {"detail": "Not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = TitleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    conversation.title = serializer.validated_data["title"][:100]
    conversation.save()

    return Response(status=status.HTTP_204_NO_CONTENT)



@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def conversation_soft_delete(request, pk):
    try:
        conversation = Conversation.objects.get(pk=pk)
    except Conversation.DoesNotExist:
        return Response(
            {"detail": "Not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    conversation.deleted_at = timezone.now()
    conversation.save()

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([AllowAny])
def conversation_manage(request, pk):
    return Response({"detail": "Not implemented yet"})


@api_view(["POST"])
@permission_classes([AllowAny])
def conversation_add_version(request, pk):
    return Response({"detail": "Not implemented yet"})


@api_view(["PUT"])
@permission_classes([AllowAny])
def conversation_switch_version(request, pk, version_id):
    return Response({"detail": "Not implemented yet"})


@api_view(["POST"])
@permission_classes([AllowAny])
def version_add_message(request, pk):
    return Response({"detail": "Not implemented yet"})



# Task 8: Conversation summaries (pagination + filter)

@api_view(["GET"])
@permission_classes([AllowAny])
def conversation_summaries(request):
    """
    Returns paginated conversation summaries.
    Supports filtering via `search`.
    """
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

    serializer = ConversationSummarySerializer(
        page.object_list, many=True
    )

    return Response({
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page.number,
        "results": serializer.data,
    })


# Task 9: File upload with duplicate prevention
@api_view(["POST"])
@permission_classes([AllowAny])
def upload_file(request):
    """
    Upload file and prevent duplicates using SHA-256 hash.
    """
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
    )

    return Response(
        FileUploadSerializer(uploaded_file).data,
        status=status.HTTP_201_CREATED,
    )

# Task 10: List uploaded files with metadata
@api_view(["GET"])
@permission_classes([AllowAny])
def list_uploaded_files(request):
    """
    List all uploaded files.
    """
    files = UploadedFile.objects.all().order_by("-uploaded_at")
    serializer = FileListSerializer(files, many=True)
    return Response(serializer.data)

# Task 11: Delete uploaded file
@api_view(["DELETE"])
@permission_classes([AllowAny])
def delete_uploaded_file(request, pk):
    """
    Delete uploaded file by ID.
    """
    file_obj = get_object_or_404(UploadedFile, pk=pk)
    file_obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
