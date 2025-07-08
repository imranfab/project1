from django.contrib import admin
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from nested_admin.nested import NestedModelAdmin, NestedStackedInline, NestedTabularInline

from chat.models import Conversation, Message, Role, Version, FileUpload


# Custom Form for FileUpload

class FileUploadForm(ModelForm):
    class Meta:
        model = FileUpload
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')

        if file:
            import hashlib
            hash_obj = hashlib.sha256()
            for chunk in file.chunks():
                hash_obj.update(chunk)
            file_hash = hash_obj.hexdigest()

            # Check if the same file already exists
            if FileUpload.objects.filter(file_hash=file_hash).exclude(pk=self.instance.pk).exists():
                raise ValidationError("⚠️ File already exists in the system (duplicate content).")

            # Store the hash
            cleaned_data['file_hash'] = file_hash

        return cleaned_data


class FileUploadAdmin(admin.ModelAdmin):
    form = FileUploadForm
    readonly_fields = ('file_hash', 'uploaded_at')  # Hide from editable fields
    fields = ('file', 'original_name')  # Only show editable fields
    list_display = ('original_name', 'file_hash', 'uploaded_at')  # Optional display


# Rest of your admin setup


class RoleAdmin(NestedModelAdmin):
    list_display = ["id", "name"]

class MessageAdmin(NestedModelAdmin):
    list_display = ["display_desc", "role", "id", "created_at", "version"]

    def display_desc(self, obj):
        return obj.content[:20] + "..."
    display_desc.short_description = "content"

class MessageInline(NestedTabularInline):
    model = Message
    extra = 2

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
        if self.value() == "True":
            return queryset.filter(deleted_at__isnull=False)
        elif self.value() == "False":
            return queryset.filter(deleted_at__isnull=True)
        return queryset

class ConversationAdmin(NestedModelAdmin):
    actions = ["undelete_selected", "soft_delete_selected"]
    inlines = [VersionInline]
    list_display = ("title", "id", "created_at", "modified_at", "deleted_at", "version_count", "is_deleted", "user", "summary")
    list_filter = (DeletedListFilter, 'created_at', 'user')
    search_fields = ('title', 'summary', 'user__username')
    list_per_page = 10
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
            if choice[0] == "delete_selected":
                choices[idx] = ("delete_selected", "Hard delete selected conversations")
        return choices

    def is_deleted(self, obj):
        return obj.deleted_at is not None
    is_deleted.boolean = True
    is_deleted.short_description = "Deleted?"

class VersionAdmin(NestedModelAdmin):
    inlines = [MessageInline]
    list_display = ("id", "conversation", "parent_version", "root_message")


# Register all models

admin.site.register(Role, RoleAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Version, VersionAdmin)
admin.site.register(FileUpload, FileUploadAdmin)
