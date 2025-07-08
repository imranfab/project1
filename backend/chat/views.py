from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes



from chat.models import Conversation, Message, Version
from chat.serializers import ConversationSerializer, MessageSerializer, TitleSerializer, VersionSerializer
from chat.utils.branching import make_branched_conversation
# task-3 imports-1.0  Destroyapi view -3.4 delete file end point
from rest_framework.generics import ListAPIView
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from chat.serializers import ConversationSummarySerializer

# task-3.2file upload with duplicate check
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UploadedFileSerializer
# task-3.3 List Uploaded Files with Metadata
from .models import FileUpload

class FileUploadView(APIView):
    def post(self, request):
        serializer = UploadedFileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    
class FileListView(ListAPIView):
    queryset = FileUpload.objects.all().order_by('-uploaded_at')
    serializer_class = UploadedFileSerializer




    

# task 3-1.0
class ConversationSummaryListView(ListAPIView):
    queryset = Conversation.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    serializer_class = ConversationSummarySerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'summary']

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(user=user, deleted_at__isnull=True).order_by('-created_at')
# end----------------------


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
# task-4 imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


from .models import FileUpload
from .serializers import UploadedFileSerializer

import logging
from .models import FileLog

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file_view(request):
    if not request.user.is_staff:
        return Response({'detail': 'Permission denied. Admins only.'}, status=403)

    if 'file' not in request.FILES:
        return Response({'error': 'No file provided.'}, status=400)

    file_obj = request.FILES['file']
    uploaded_file =FileUpload.objects.create(user=request.user, file=file_obj)

    # Log to console
    logger.info(f"{request.user.email} uploaded file: {file_obj.name}")

    #  Log to DataBase
    FileLog.objects.create(user=request.user, file_name=file_obj.name, action='UPLOAD')

    return Response({'message': 'File uploaded successfully.'}, status=201)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_uploaded_file(request, file_id):
    try:
        uploaded_file = FileUpload.objects.get(id=file_id)
        file_name = uploaded_file.file.name
        uploaded_file.delete()

        #  Create a FileLog entry
        FileLog.objects.create(
            user=request.user,
            action='DELETE',
            file_name=file_name
        )

        logger.info(f"{request.user.email} deleted file: {file_name}")
        return Response({'message': 'File deleted successfully.'}, status=200)
    except FileUpload.DoesNotExist:
        return Response({'error': 'File not found.'}, status=404)


from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from chat.models import Conversation

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_summary(request, id):
    cache_key = f"conversation_summary_{id}"
    summary = cache.get(cache_key)

    if summary is None:
        try:
            conversation = Conversation.objects.get(id=id, user=request.user)
        except Conversation.DoesNotExist:
            return Response({"error": "Conversation not found"}, status=404)

        summary = conversation.summary or "No summary available"
        cache.set(cache_key, summary, timeout=3600)  # cache for 1 hour

    return Response({"id": id, "summary": summary})

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': { 'class': 'logging.StreamHandler' },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}









