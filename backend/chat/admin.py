from django.contrib import admin
from django.utils import timezone
from nested_admin.nested import NestedModelAdmin, NestedStackedInline, NestedTabularInline
from .models import Conversation, Message, Role, Version

class MessageInline(NestedTabularInline):
    model = Message
    extra = 2

class VersionInline(NestedStackedInline):
    model = Version
    extra = 1
    inlines = [MessageInline]

class ConversationAdmin(NestedModelAdmin):
    actions = ["undelete_selected", "soft_delete_selected"]
    inlines = [VersionInline]
    list_display = ("id", "title", "short_summary", "created_at", "modified_at", "deleted_at", "version_count", "is_deleted")
    list_filter = ()
    ordering = ("-modified_at",)

    def is_deleted(self, obj):
        return obj.deleted_at is not None
    is_deleted.boolean = True
    is_deleted.short_description = "Deleted?"

    def short_summary(self, obj):
        s = getattr(obj, "summary", "") or ""
        return (s[:80] + "…") if len(s) > 80 else s
    short_summary.short_description = "Summary"

    def undelete_selected(self, request, queryset):
        queryset.update(deleted_at=None)
    undelete_selected.short_description = "Undelete selected conversations"

    def soft_delete_selected(self, request, queryset):
        queryset.update(deleted_at=timezone.now())
    soft_delete_selected.short_description = "Soft delete selected conversations"

admin.site.register(Role)
admin.site.register(Message)
admin.site.register(Version)
admin.site.register(Conversation, ConversationAdmin)
