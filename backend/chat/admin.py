from django.contrib import admin
from django.utils import timezone
from nested_admin.nested import NestedModelAdmin, NestedStackedInline, NestedTabularInline

from chat.models import Conversation, Message, Role, Version,UploadedFile
from django.utils.html import format_html

class RoleAdmin(NestedModelAdmin):
    list_display = ["id", "name"]


class MessageAdmin(NestedModelAdmin):
    list_display = ["display_desc", "role", "id", "created_at", "version"]

    def display_desc(self, obj):
        return obj.content[:20] + "..."

    display_desc.short_description = "content"


class MessageInline(NestedTabularInline):
    model = Message
    extra = 2  # number of extra forms to display


class VersionInline(NestedStackedInline):
    model = Version
    extra = 1
    inlines = [MessageInline]


class DeletedListFilter(admin.SimpleListFilter):
    title = "Deleted"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return (
            ("True", "Yes"),
            ("False", "No"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "True":
            return queryset.filter(deleted_at__isnull=False)
        elif value == "False":
            return queryset.filter(deleted_at__isnull=True)
        return queryset


class ConversationAdmin(NestedModelAdmin):
    actions = ["undelete_selected", "soft_delete_selected"]
    inlines = [VersionInline]
    list_display = ("title", "id", "created_at", "modified_at","short_summary",  "deleted_at", "version_count", "is_deleted", "user")
    list_filter = (DeletedListFilter,)
    ordering = ("-modified_at",)
    readonly_fields = ("summary",)  
    fields = (
        "title",
        "summary",  
        "user",
        "deleted_at",
    )
    def short_summary(self, obj):
        return (obj.summary[:50] + "...") if obj.summary else "— No summary generated "
    short_summary.short_description = "Summary"


    def undelete_selected(self, request, queryset):
        queryset.update(deleted_at=None)

    undelete_selected.short_description = "Undelete selected conversations"

    def soft_delete_selected(self, request, queryset):
        queryset.update(deleted_at=timezone.now())

    soft_delete_selected.short_description = "Soft delete selected conversations"

    def get_action_choices(self, request, **kwargs):
        choices = super().get_action_choices(request)
        for idx, choice in enumerate(choices):
            fn_name = choice[0]
            if fn_name == "delete_selected":
                new_choice = (fn_name, "Hard delete selected conversations")
                choices[idx] = new_choice
        return choices

    def is_deleted(self, obj):
        return obj.deleted_at is not None

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted?"


class VersionAdmin(NestedModelAdmin):
    inlines = [MessageInline]
    list_display = ("id", "conversation", "parent_version", "root_message")



# NEW: UploadedFile Admin
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'user', 'file_size_display', 'file_type', 'uploaded_at', 'file_link')
    list_filter = ('file_type', 'uploaded_at')
    search_fields = ('original_filename', 'user__username', 'user__email', 'file_hash')
    readonly_fields = ('id', 'file_hash', 'file_size', 'file_type', 'uploaded_at', 'file_preview')
    
    fieldsets = (
        ('File Information', {
            'fields': ('id', 'file', 'file_preview', 'original_filename', 'file_type')
        }),
        ('Metadata', {
            'fields': ('file_size', 'file_hash', 'uploaded_at', 'user')
        }),
    )
    
    @admin.display(description="File Size")
    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    @admin.display(description="File Link")
    def file_link(self, obj):
        """Display download link for file"""
        if obj.file:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.file.url)
        return "No file"
    
    @admin.display(description="Preview")
    def file_preview(self, obj):
        """Display image preview if file is an image"""
        if obj.file and obj.file_type.startswith('image/'):
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.file.url)
        return "No preview available"


admin.site.register(Role, RoleAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Version, VersionAdmin)
admin.site.register(UploadedFile, UploadedFileAdmin)
