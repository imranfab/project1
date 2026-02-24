"""
Task 1, 3, 4: Add summary fields to Conversation, create UploadedFile and FileAccessLog.

IMPORTANT: Check what your last migration is called first:
    ls backend/chat/migrations/
Then update the `dependencies` line below to match.
"""

import django.db.models.deletion
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    # ↓ Change '0005_some_name' to whatever your LAST migration file is called
    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        # Task 1: summary fields on Conversation
        migrations.AddField(
            model_name="conversation",
            name="summary",
            field=models.TextField(
                blank=True, default="",
                help_text="Auto-generated summary of the conversation.",
            ),
        ),
        migrations.AddField(
            model_name="conversation",
            name="summary_generated_at",
            field=models.DateTimeField(
                blank=True, null=True,
                help_text="When the summary was last generated.",
            ),
        ),
        # Task 3: UploadedFile model
        migrations.CreateModel(
            name="UploadedFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("uploaded_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="uploaded_files",
                    to="authentication.customuser",
                )),
                ("original_filename", models.CharField(max_length=255)),
                ("file", models.FileField(upload_to="uploads/")),
                ("content_type", models.CharField(max_length=100)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("sha256", models.CharField(max_length=64)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-uploaded_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="uploadedfile",
            unique_together={("uploaded_by", "sha256")},
        ),
        # Task 4: FileAccessLog model
        migrations.CreateModel(
            name="FileAccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("file", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="access_logs",
                    to="chat.uploadedfile",
                )),
                ("performed_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="file_actions",
                    to="authentication.customuser",
                )),
                ("action", models.CharField(
                    choices=[("upload", "Upload"), ("delete", "Delete"), ("list", "List")],
                    max_length=20,
                )),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("extra", models.JSONField(blank=True, default=dict)),
            ],
            options={"ordering": ["-timestamp"]},
        ),
    ]
