from django.urls import path
from chat import views

urlpatterns = [
    path("", views.chat_root_view),

    
    path(
        "conversations/summaries/",
        views.conversation_summaries,
    ),

    # Conversations
    path("conversations/", views.get_conversations),
    path("conversations_branched/", views.get_conversations_branched),

    path("conversation_branched/<uuid:pk>/", views.get_conversation_branched),

    path("conversations/add/", views.add_conversation),

    path(
        "conversations/<uuid:pk>/messages/",
        views.conversation_add_message,
    ),
    path(
        "conversations/<uuid:pk>/add_message/",
        views.conversation_add_message,
    ),

    # Files
    path("files/upload/", views.upload_file),
    path("files-uploaded/", views.list_uploaded_files),
    path("files/<int:pk>/", views.delete_uploaded_file),
]
