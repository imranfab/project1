"""
Task 4: Tests for all new features.
Run: python manage.py test chat
"""

import hashlib
from datetime import timedelta

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from authentication.models import CustomUser
from chat.models import Conversation, FileAccessLog, Message, Role, UploadedFile, Version
from chat.summary import _build_transcript


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email="test@test.com", password="pass1234", staff=False):
    user = CustomUser.objects.create_user(username=email, email=email, password=password)
    user.is_staff = staff
    user.save()
    return user


def make_file_manager(email="manager@test.com"):
    user = make_user(email=email)
    grp, _ = Group.objects.get_or_create(name="file_managers")
    user.groups.add(grp)
    return user


def make_conversation(user, title="Test", days_old=0):
    conv = Conversation.objects.create(user=user, title=title)
    if days_old:
        Conversation.objects.filter(pk=conv.pk).update(
            modified_at=timezone.now() - timedelta(days=days_old)
        )
        conv.refresh_from_db()
    return conv


def make_file(user, filename="test.txt", content=b"hello"):
    sha256 = hashlib.sha256(content).hexdigest()
    f = SimpleUploadedFile(filename, content, content_type="text/plain")
    return UploadedFile.objects.create(
        uploaded_by=user, original_filename=filename, file=f,
        content_type="text/plain", size_bytes=len(content), sha256=sha256,
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class ConversationModelTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_summary_defaults_empty(self):
        conv = make_conversation(self.user)
        self.assertEqual(conv.summary, "")
        self.assertIsNone(conv.summary_generated_at)

    def test_summary_can_be_saved(self):
        conv = make_conversation(self.user)
        conv.summary = "This is a test summary."
        conv.summary_generated_at = timezone.now()
        conv.save()
        conv.refresh_from_db()
        self.assertEqual(conv.summary, "This is a test summary.")


class UploadedFileModelTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_soft_delete(self):
        f = make_file(self.user)
        f.soft_delete()
        self.assertTrue(f.is_deleted)
        self.assertIsNotNone(f.deleted_at)

    def test_sha256_computed_correctly(self):
        content = b"unique content"
        upload = SimpleUploadedFile("f.txt", content)
        result = UploadedFile.compute_sha256(upload)
        self.assertEqual(result, hashlib.sha256(content).hexdigest())

    def test_duplicate_raises_error(self):
        from django.db import IntegrityError
        content = b"same content"
        make_file(self.user, content=content)
        with self.assertRaises(IntegrityError):
            make_file(self.user, filename="copy.txt", content=content)


# ---------------------------------------------------------------------------
# Summary tests
# ---------------------------------------------------------------------------

class SummaryTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.user_role, _ = Role.objects.get_or_create(name="user")
        self.assistant_role, _ = Role.objects.get_or_create(name="assistant")

    def _make_conv_with_messages(self):
        conv = make_conversation(self.user)
        version = Version.objects.create(conversation=conv)
        conv.active_version = version
        conv.save()
        Message.objects.create(version=version, role=self.user_role, content="Hello!")
        Message.objects.create(version=version, role=self.assistant_role, content="Hi there!")
        return conv

    def test_transcript_built_correctly(self):
        conv = self._make_conv_with_messages()
        transcript = _build_transcript(conv)
        self.assertIn("Hello!", transcript)
        self.assertIn("Hi there!", transcript)

    def test_empty_transcript_for_no_messages(self):
        conv = make_conversation(self.user)
        self.assertEqual(_build_transcript(conv), "")

    @patch("chat.summary.openai")
    def test_generate_summary_saves(self, mock_openai):
        from chat.summary import generate_summary
        conv = self._make_conv_with_messages()
        mock_openai.ChatCompletion.create.return_value = {
            "choices": [{"message": {"content": "A summary."}}]
        }
        result = generate_summary(conv)
        conv.refresh_from_db()
        self.assertEqual(result, "A summary.")
        self.assertEqual(conv.summary, "A summary.")

    @patch("chat.summary.openai")
    def test_generate_summary_handles_failure(self, mock_openai):
        from chat.summary import generate_summary
        conv = self._make_conv_with_messages()
        mock_openai.ChatCompletion.create.side_effect = Exception("API down")
        result = generate_summary(conv)
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# API: Summary endpoints
# ---------------------------------------------------------------------------

class SummaryAPITest(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.conv1 = make_conversation(self.user, title="Conv A")
        self.conv1.summary = "Summary A"
        self.conv1.save()
        self.conv2 = make_conversation(self.user, title="Conv B")

    def test_list_returns_own_conversations(self):
        response = self.client.get("/chat/summaries/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_filter_has_summary_true(self):
        response = self.client.get("/chat/summaries/?has_summary=true")
        self.assertEqual(response.data["count"], 1)

    def test_filter_has_summary_false(self):
        response = self.client.get("/chat/summaries/?has_summary=false")
        self.assertEqual(response.data["count"], 1)

    def test_search_by_title(self):
        response = self.client.get("/chat/summaries/?search=Conv+A")
        self.assertEqual(response.data["count"], 1)

    def test_unauthenticated_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/chat/summaries/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# API: File upload
# ---------------------------------------------------------------------------

class FileUploadAPITest(APITestCase):
    def setUp(self):
        self.manager = make_file_manager()
        self.regular = make_user(email="regular@test.com")
        self.client.force_authenticate(user=self.manager)

    def test_upload_success(self):
        f = SimpleUploadedFile("hello.txt", b"hello world", content_type="text/plain")
        response = self.client.post("/chat/files/upload/", {"file": f}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("sha256", response.data)

    def test_duplicate_rejected(self):
        content = b"duplicate content"
        f1 = SimpleUploadedFile("a.txt", content, content_type="text/plain")
        f2 = SimpleUploadedFile("b.txt", content, content_type="text/plain")
        self.client.post("/chat/files/upload/", {"file": f1}, format="multipart")
        response = self.client.post("/chat/files/upload/", {"file": f2}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_regular_user_cannot_upload(self):
        self.client.force_authenticate(user=self.regular)
        f = SimpleUploadedFile("x.txt", b"data", content_type="text/plain")
        response = self.client.post("/chat/files/upload/", {"file": f}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_creates_log(self):
        f = SimpleUploadedFile("log.txt", b"log content", content_type="text/plain")
        self.client.post("/chat/files/upload/", {"file": f}, format="multipart")
        self.assertTrue(FileAccessLog.objects.filter(action="upload").exists())


# ---------------------------------------------------------------------------
# API: File list and delete
# ---------------------------------------------------------------------------

class FileListDeleteAPITest(APITestCase):
    def setUp(self):
        self.manager = make_file_manager()
        self.client.force_authenticate(user=self.manager)
        self.file = make_file(self.manager, content=b"my file content")

    def test_list_files(self):
        response = self.client.get("/chat/files/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_deleted_files_not_shown(self):
        self.file.soft_delete()
        response = self.client.get("/chat/files/")
        self.assertEqual(response.data["count"], 0)

    def test_delete_file(self):
        response = self.client.delete(f"/chat/files/{self.file.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.file.refresh_from_db()
        self.assertTrue(self.file.is_deleted)

    def test_other_user_cannot_delete(self):
        other = make_file_manager(email="other@test.com")
        self.client.force_authenticate(user=other)
        response = self.client.delete(f"/chat/files/{self.file.pk}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Management command test
# ---------------------------------------------------------------------------

class CleanupCommandTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_deletes_old_conversations(self):
        old = make_conversation(self.user, days_old=100)
        fresh = make_conversation(self.user, days_old=10)
        from django.core.management import call_command
        call_command("cleanup_conversations", days=90, verbosity=0)
        self.assertFalse(Conversation.objects.filter(pk=old.pk).exists())
        self.assertTrue(Conversation.objects.filter(pk=fresh.pk).exists())

    def test_dry_run_does_not_delete(self):
        old = make_conversation(self.user, days_old=100)
        from django.core.management import call_command
        call_command("cleanup_conversations", days=90, dry_run=True, verbosity=0)
        self.assertTrue(Conversation.objects.filter(pk=old.pk).exists())
