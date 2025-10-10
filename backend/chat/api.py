from rest_framework import viewsets, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from .models import Conversation, Message
from .serializers import ConversationSummarySerializer, MessageSerializer

class SmallPage(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/conversations/
    GET /api/conversations/<uuid>/
    """
    queryset = Conversation.objects.order_by("-modified_at")
    serializer_class = ConversationSummarySerializer
    pagination_class = SmallPage
    permission_classes = [permissions.AllowAny]  # loosen for dev
    filter_backends = [SearchFilter]
    search_fields = ["title", "summary"]

class MessageViewSet(viewsets.ModelViewSet):
    """
    GET /api/messages/
    GET /api/messages/<uuid>/
    Optional filters:
      ?conversation=<conversation_uuid>
      ?version=<version_uuid>
      ?search=hello  (searches content, role name, conversation title)
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = SmallPage
    filter_backends = [SearchFilter]
    search_fields = ["content", "role__name", "version__conversation__title"]

    def get_queryset(self):
        qs = (Message.objects
              .select_related("role", "version", "version__conversation")
              .order_by("-created_at"))
        conv_id = self.request.query_params.get("conversation")
        ver_id = self.request.query_params.get("version")
        if conv_id:
            qs = qs.filter(version__conversation_id=conv_id)
        if ver_id:
            qs = qs.filter(version_id=ver_id)
        return qs