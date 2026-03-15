from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class ChatKeyBackupApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="guest@example.com",
            username="Guest User",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

    def test_user_can_store_and_fetch_wrapped_chat_key_backup(self):
        payload = {
            "public_key": "public-key",
            "key_algorithm": "RSA-OAEP-256",
            "key_version": 1,
            "encrypted_private_key": "encrypted-private-key",
            "backup_iv": "backup-iv",
            "backup_salt": "backup-salt",
            "backup_kdf": "PBKDF2-SHA256",
            "backup_kdf_iterations": 600000,
            "backup_cipher": "AES-GCM",
            "backup_version": 1,
        }

        store_response = self.client.post(
            reverse("auth-me-chat-key"),
            payload,
            format="json",
        )
        self.assertEqual(store_response.status_code, status.HTTP_200_OK)
        self.assertTrue(store_response.data["has_backup"])

        fetch_response = self.client.get(reverse("auth-me-chat-key"))
        self.assertEqual(fetch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(fetch_response.data["public_key"], payload["public_key"])
        self.assertEqual(
            fetch_response.data["encrypted_private_key"],
            payload["encrypted_private_key"],
        )
        self.assertEqual(fetch_response.data["backup_kdf"], payload["backup_kdf"])

    def test_invalid_backup_cipher_is_rejected(self):
        response = self.client.post(
            reverse("auth-me-chat-key"),
            {
                "public_key": "public-key",
                "key_algorithm": "RSA-OAEP-256",
                "key_version": 1,
                "encrypted_private_key": "encrypted-private-key",
                "backup_iv": "backup-iv",
                "backup_salt": "backup-salt",
                "backup_kdf": "PBKDF2-SHA256",
                "backup_kdf_iterations": 600000,
                "backup_cipher": "AES-CBC",
                "backup_version": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
