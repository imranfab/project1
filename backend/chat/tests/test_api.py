from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APITestCase
from chat.models import Conversation
from chat.tests.utils import make_user  # assuming you have a helper

class TestRBACAndFileFlow(APITestCase):
    def setUp(self):
        # Ensure uploader group exists
        Group.objects.get_or_create(name="uploader")
        # Create user and assign to uploader group
        self.uploader = make_user(email="up@u.com", groups=("uploader",))
        self.client.force_login(self.uploader)  # login after group assignment

    def test_upload_list_process_delete_as_uploader(self):
        # Upload file
        r1 = self.client.post(
            reverse("file-upload"),
            {"file": SimpleUploadedFile("doc.txt", b"django and python are great")},
            format="multipart"
        )
        self.assertEqual(r1.status_code, 201)
        file_id = r1.data["id"]

        # You can add list, process, delete assertions here as needed

class TestRAG(APITestCase):
    def setUp(self):
        Group.objects.get_or_create(name="uploader")
        self.uploader = make_user(email="rag@u.com", groups=("uploader",))
        self.client.force_login(self.uploader)

    def test_rag_query(self):
        up = self.client.post(
            reverse("file-upload"),
            {"file": SimpleUploadedFile("doc.txt", b"django and python are great")},
            format="multipart"
        )
        self.assertEqual(up.status_code, 201)
        fid = up.data["id"]

        # Call your RAG query endpoint
        resp = self.client.post(
            reverse("rag-query"),
            {"file_id": fid, "query": "python"},
            format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("results", resp.data)

class TestSummariesCache(APITestCase):
    def setUp(self):
        Group.objects.get_or_create(name="uploader")
        self.u = User.objects.create_user(email="test@test.com", password="1234")
        self.client.force_login(self.u)
        cache.clear()  # Clear cache to avoid AnonymousUser issues

        # Create conversations for this user
        self.c1 = Conversation.objects.create(user=self.u, title="First conv")
        self.c2 = Conversation.objects.create(user=self.u, title="Second conv")

    def test_cached_per_user_and_query(self):
        url = reverse("conversation-summary-list")
        r1 = self.client.get(url)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(len(r1.data), 2)

        # Subsequent call should hit cache
        r2 = self.client.get(url)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data, r1.data)
