from django.contrib import admin
from django.utils.html import format_html

from .models import Conversation, FileAccessLog, Message, Role, UploadedFile, Version


class VersionInline(admin.TabularInline):
    model = Version
    extra = 0
    show_change_link = True


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "user",
        "summary_preview",       # Task 1: show summary
        "summary_generated_at",  # Task 1: show when generated
        "created_at",
        "modified_at",
        "version_count",
    ]
    search_fields = ["title", "user__email", "summary"]
    list_filter = ["created_at", "user"]
    readonly_fields = ["created_at", "modified_at", "summary_generated_at"]
    inlines = [VersionInline]
    fieldsets = [
        ("Basic Info", {
            "fields": ["user", "title", "active_version", "deleted_at", "created_at", "modified_at"]
        }),
        ("Summary (Task 1)", {
            "fields": ["summary", "summary_generated_at"],
            "description": "Auto-generated conversation summary.",
        }),
    ]

    @admin.display(description="Summary")
    def summary_preview(self, obj):
        if obj.summary:
            return obj.summary[:80] + ("…" if len(obj.summary) > 80 else "")
        return format_html("<em style='color:gray'>No summary yet</em>")


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "parent_version", "root_message"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "role", "short_content", "created_at", "version"]
    list_filter = ["role"]
    search_fields = ["content"]

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:80]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ["original_filename", "uploaded_by", "size_bytes", "uploaded_at", "is_deleted"]
    list_filter = ["is_deleted", "uploaded_at"]
    search_fields = ["original_filename", "uploaded_by__email"]
    readonly_fields = ["sha256", "uploaded_at", "deleted_at", "size_bytes"]


@admin.register(FileAccessLog)
class FileAccessLogAdmin(admin.ModelAdmin):
    list_display = ["action", "performed_by", "file", "ip_address", "timestamp"]
    list_filter = ["action", "timestamp"]
    readonly_fields = ["timestamp"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
