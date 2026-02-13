from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count,Q
from chat.models import Conversation, Message, Version , UploadedFile
from chat.serializers import ConversationSerializer, MessageSerializer, TitleSerializer, VersionSerializer,ConversationSummarySerializer,UploadedFileSerializer,SummaryPagination
from chat.utils.branching import make_branched_conversation
from rest_framework.decorators import parser_classes
from rest_framework.parsers import MultiPartParser, FormParser


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
        # return Response(serializer.data, status=status.HTTP_201_CREATED)
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

    # Check if root message belongs to the same conversation
    if root_message.version.conversation != conversation:
        return Response({"detail": "Root message not part of the conversation"}, status=status.HTTP_400_BAD_REQUEST)

    new_version = Version.objects.create(
        conversation=conversation, parent_version=root_message.version, root_message=root_message
    )

    # Copy messages before root_message to new_version
    messages_before_root = Message.objects.filter(version=version, created_at__lt=root_message.created_at)
    new_messages = [
        Message(content=message.content, role=message.role, version=new_version) for message in messages_before_root
    ]
    Message.objects.bulk_create(new_messages)

    # Set the new version as the current version
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


@login_required
@api_view(["GET"])
def get_conversation_summaries(request):
    """
    API endpoint to retrieve conversation summaries with pagination and filtering.
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of items per page (default: 10, max: 100)
    - search: Search in title and summary
    - created_after: Filter by creation date (YYYY-MM-DD)
    - created_before: Filter by creation date (YYYY-MM-DD)
    - has_summary: Filter conversations with/without summaries (true/false)
    """
    
    # Get queryset
    queryset = Conversation.objects.filter(
        user=request.user, 
        deleted_at__isnull=True
    ).annotate(
        version_count=Count('versions')
    ).select_related('user', 'active_version').order_by('-modified_at')
    
    # Apply filters
    search = request.GET.get('search', None)
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(summary__icontains=search)
        )
    
    created_after = request.GET.get('created_after', None)
    if created_after:
        queryset = queryset.filter(created_at__gte=created_after)
    
    created_before = request.GET.get('created_before', None)
    if created_before:
        queryset = queryset.filter(created_at__lte=created_before)
    
    has_summary = request.GET.get('has_summary', None)
    if has_summary is not None:
        if has_summary.lower() == 'true':
            queryset = queryset.filter(summary__isnull=False).exclude(summary='')
        elif has_summary.lower() == 'false':
            queryset = queryset.filter(Q(summary__isnull=True) | Q(summary=''))
    
    # Paginate
    paginator = SummaryPagination()
    paginated_queryset = paginator.paginate_queryset(queryset, request)
    
    # Serialize
    serializer = ConversationSummarySerializer(paginated_queryset, many=True, context={'request': request})
    
    return paginator.get_paginated_response(serializer.data)


@login_required
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_file(request):
    """
    API endpoint to upload a file with duplicate detection.
    
    Request:
    - file: File to upload (multipart/form-data)
    
    Returns:
    - 201: File uploaded successfully
    - 400: Validation error or duplicate file
    """
    
    if 'file' not in request.FILES:
        return Response(
            {"detail": "No file provided"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    file = request.FILES['file']
    
    # Create serializer with file and user
    serializer = UploadedFileSerializer(
        data={'file': file, 'user': request.user.id},
        context={'request': request}
    )
    
    try:
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"detail": str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@login_required
@api_view(["GET"])
def list_uploaded_files(request):
    """
    API endpoint to list uploaded files with metadata and filtering.
    
    Query Parameters:
    - file_type: Filter by file type (e.g., 'image/png')
    - uploaded_after: Filter by upload date (YYYY-MM-DD)
    - uploaded_before: Filter by upload date (YYYY-MM-DD)
    - search: Search in filename
    - page: Page number
    - page_size: Items per page
    """
    
    # Get queryset
    queryset = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at')
    
    # Apply filters
    file_type = request.GET.get('file_type', None)
    if file_type:
        queryset = queryset.filter(file_type__icontains=file_type)
    
    uploaded_after = request.GET.get('uploaded_after', None)
    if uploaded_after:
        queryset = queryset.filter(uploaded_at__gte=uploaded_after)
    
    uploaded_before = request.GET.get('uploaded_before', None)
    if uploaded_before:
        queryset = queryset.filter(uploaded_at__lte=uploaded_before)
    
    search = request.GET.get('search', None)
    if search:
        queryset = queryset.filter(original_filename__icontains=search)
    
    # Paginate
    paginator = SummaryPagination()
    paginated_queryset = paginator.paginate_queryset(queryset, request)
    
    # Serialize
    serializer = UploadedFileSerializer(
        paginated_queryset, 
        many=True, 
        context={'request': request}
    )
    
    return paginator.get_paginated_response(serializer.data)


@login_required
@api_view(["GET"])
def get_uploaded_file(request, pk):
    """
    API endpoint to get details of a specific uploaded file.
    """
    try:
        uploaded_file = UploadedFile.objects.get(pk=pk, user=request.user)
    except UploadedFile.DoesNotExist:
        return Response(
            {"detail": "File not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = UploadedFileSerializer(uploaded_file, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@login_required
@api_view(["DELETE"])
def delete_uploaded_file(request, pk):
    """
    API endpoint to delete an uploaded file.
    
    Deletes both the database record and the physical file.
    """
    try:
        uploaded_file = UploadedFile.objects.get(pk=pk, user=request.user)
    except UploadedFile.DoesNotExist:
        return Response(
            {"detail": "File not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Delete the file (this also deletes the physical file due to model override)
    filename = uploaded_file.original_filename
    uploaded_file.delete()
    
    return Response(
        {"detail": f"File '{filename}' deleted successfully"}, 
        status=status.HTTP_200_OK
    )
