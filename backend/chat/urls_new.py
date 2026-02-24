"""
Task 3: New URL patterns. These are added into the existing chat/urls.py
"""

from django.urls import path

from .views_new import (
    ConversationSummaryDetailView,
    ConversationSummaryListView,
    FileDeleteView,
    FileListView,
    FileUploadView,
)

# Add these to the existing urlpatterns list in chat/urls.py
new_urlpatterns = [
    path("summaries/", ConversationSummaryListView.as_view(), name="summary-list"),
    path("summaries/<uuid:pk>/", ConversationSummaryDetailView.as_view(), name="summary-detail"),
    path("files/upload/", FileUploadView.as_view(), name="file-upload"),
    path("files/", FileListView.as_view(), name="file-list"),
    path("files/<int:pk>/", FileDeleteView.as_view(), name="file-delete"),
]
