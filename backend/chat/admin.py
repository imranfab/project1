from django.contrib import admin
from django.utils import timezone
from nested_admin.nested import NestedModelAdmin, NestedStackedInline, NestedTabularInline

from chat.models import Conversation, Message, Role, Version
# task-3
from .models import FileUpload
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError


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
    list_display = ("title", "id", "created_at", "modified_at", "deleted_at", "version_count", "is_deleted", "user","summary")
    list_filter = (DeletedListFilter,)
    ordering = ("-modified_at",)

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

# task-3 upload file
# Custom form to show only user and file (hide hash/size in input)
class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['user', 'file']  # only show user and file fields
@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    form = FileUploadForm
    list_display = ("id", "file_name", "file_size", "file_hash", "uploaded_at", "user")
    readonly_fields = ("file_name", "file_size", "file_hash", "uploaded_at")

    def save_model(self, request, obj, form, change):
        try:
            obj.save()  # Triggers full_clean() with validation
            self.message_user(request, "File uploaded successfully.", level=messages.SUCCESS)
        except ValidationError as e:
            self.message_user(
                request,
                f"Upload failed: {e.messages[0]}",
                level=messages.WARNING
            )



class VersionAdmin(NestedModelAdmin):
    inlines = [MessageInline]
    list_display = ("id", "conversation", "parent_version", "root_message")


admin.site.register(Role, RoleAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Version, VersionAdmin)
