"""
Task 3 & 4: New API views for conversation summaries and file management.
"""

import logging

from django.core.cache import cache
from rest_framework import filters, generics, permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, FileAccessLog, UploadedFile
from .permissions import IsFileManager
from .serializers_new import (
    ConversationSummarySerializer,
    FileUploadSerializer,
    UploadedFileSerializer,
)
from .summary import generate_summary

logger = logging.getLogger("chat.files")

CACHE_TIMEOUT = 60 * 10  # 10 minutes


def _log(action, user, request, file=None, extra=None):
    """Save a FileAccessLog entry and write to log file."""
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
    FileAccessLog.objects.create(
        file=file,
        performed_by=user,
        action=action,
        ip_address=ip,
        extra=extra or {},
    )
    logger.info("action=%s user=%s file=%s ip=%s", action, user.pk, getattr(file, "pk", None), ip)


# ---------------------------------------------------------------------------
# Task 3: Conversation summary endpoints
# ---------------------------------------------------------------------------

class ConversationSummaryListView(generics.ListAPIView):
    """
    GET /chat/summaries/
    Paginated list of conversations with summaries.

    Filters: has_summary=true/false, created_after=YYYY-MM-DD, created_before=YYYY-MM-DD
    Search: ?search=title
    Order: ?ordering=created_at or modified_at
    """
    serializer_class = ConversationSummarySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title"]
    ordering_fields = ["created_at", "modified_at", "title"]
    ordering = ["-modified_at"]

    def get_queryset(self):
        qs = Conversation.objects.filter(user=self.request.user, deleted_at__isnull=True)

        created_after = self.request.query_params.get("created_after")
        created_before = self.request.query_params.get("created_before")
        has_summary = self.request.query_params.get("has_summary")

        if created_after:
            qs = qs.filter(created_at__date__gte=created_after)
        if created_before:
            qs = qs.filter(created_at__date__lte=created_before)
        if has_summary == "true":
            qs = qs.exclude(summary__isnull=True).exclude(summary="")
        elif has_summary == "false":
            qs = qs.filter(summary="") | qs.filter(summary__isnull=True)

        return qs

    def list(self, request, *args, **kwargs):
        # Task 4: Cache results per user per page
        page = request.query_params.get("page", 1)
        params = request.query_params.urlencode()
        cache_key = f"summaries_{request.user.pk}_{params}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, CACHE_TIMEOUT)
        return response


class ConversationSummaryDetailView(generics.RetrieveAPIView):
    """
    GET /chat/summaries/<uuid>/
    Get summary for a single conversation.
    Pass ?regenerate=true to force a fresh summary.
    """
    serializer_class = ConversationSummarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()
        regenerate = request.query_params.get("regenerate", "false").lower() == "true"
        if regenerate or not conversation.summary:
            generate_summary(conversation)
        return Response(ConversationSummarySerializer(conversation).data)


# ---------------------------------------------------------------------------
# Task 3: File management endpoints
# ---------------------------------------------------------------------------

class FileUploadView(APIView):
    """
    POST /chat/files/upload/
    Upload a file. Duplicates (same SHA-256) are rejected with 400.
    Requires: file_managers group or staff.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated, IsFileManager]

    def post(self, request, *args, **kwargs):
        serializer = FileUploadSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        uploaded = serializer.validated_data["file"]
        sha256 = uploaded._sha256

        file_obj = UploadedFile.objects.create(
            uploaded_by=request.user,
            original_filename=uploaded.name,
            file=uploaded,
            content_type=uploaded.content_type or "application/octet-stream",
            size_bytes=uploaded.size,
            sha256=sha256,
        )

        _log(FileAccessLog.ACTION_UPLOAD, request.user, request, file=file_obj,
             extra={"filename": file_obj.original_filename})

        return Response(UploadedFileSerializer(file_obj).data, status=status.HTTP_201_CREATED)


class FileListView(generics.ListAPIView):
    """
    GET /chat/files/
    List all non-deleted files for the current user.
    """
    serializer_class = UploadedFileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["original_filename", "content_type"]
    ordering_fields = ["uploaded_at", "size_bytes", "original_filename"]
    ordering = ["-uploaded_at"]

    def get_queryset(self):
        return UploadedFile.objects.filter(uploaded_by=self.request.user, is_deleted=False)

    def list(self, request, *args, **kwargs):
        _log(FileAccessLog.ACTION_LIST, request.user, request)
        return super().list(request, *args, **kwargs)


class FileDeleteView(APIView):
    """
    DELETE /chat/files/<pk>/
    Soft-delete a file (preserves DB row for audit trail).
    Owner or staff can delete.
    """
    permission_classes = [permissions.IsAuthenticated, IsFileManager]

    def delete(self, request, pk, *args, **kwargs):
        try:
            file_obj = UploadedFile.objects.get(pk=pk, is_deleted=False)
        except UploadedFile.DoesNotExist:
            raise NotFound("File not found or already deleted.")

        if file_obj.uploaded_by != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only delete your own files.")

        _log(FileAccessLog.ACTION_DELETE, request.user, request, file=file_obj,
             extra={"filename": file_obj.original_filename})

        file_obj.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
