from datetime import date, timedelta

from asgiref.sync import async_to_sync
from channels.testing.websocket import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.bookings.models import Booking
from apps.listings.models import Listing
from apps.messaging.models import Message
from apps.messaging.services import get_or_create_conversation_for_booking
from config.asgi import application


class BookingChatBaseMixin:
    @staticmethod
    def encrypted_body_for(*, guest_id: str, host_id: str):
        return {
            "ciphertext": "c2VjdXJlLWNpcGhlcnRleHQ=",
            "iv": "MTIzNDU2Nzg5MDEy",
            "wrapped_keys": {
                guest_id: {"wrapped_key": "Z3Vlc3Qtd3JhcHBlZC1rZXk=", "key_version": 1},
                host_id: {"wrapped_key": "aG9zdC13cmFwcGVkLWtleQ==", "key_version": 1},
            },
            "algorithm": "AES-GCM",
            "key_algorithm": "RSA-OAEP-256",
            "version": 1,
            "sender_key_version": 1,
        }

    def create_booking(self, *, guest, status=Booking.Status.PENDING_PAYMENT):
        return Booking.objects.create(
            listing=self.listing,
            guest=guest,
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=9),
            num_guests=2,
            status=status,
        )

    def create_listing(self):
        return Listing.objects.create(
            host=self.host,
            title="Forest Cabin",
            description="Quiet stay in the woods.",
            location="Manali",
            category="cabins",
            price_per_night="4200.00",
            bedrooms=2,
            bathrooms="1.0",
            max_guests=4,
            amenities=["WiFi"],
            images=["https://example.com/cabin.jpg"],
            is_active=True,
        )

    def create_users(self):
        user_model = get_user_model()
        self.host = user_model.objects.create_user(
            email="host@example.com",
            username="Host User",
            password="testpass123",
        )
        self.guest = user_model.objects.create_user(
            email="guest@example.com",
            username="Guest User",
            password="testpass123",
        )
        self.stranger = user_model.objects.create_user(
            email="stranger@example.com",
            username="Stranger User",
            password="testpass123",
        )
        for index, user in enumerate((self.host, self.guest, self.stranger), start=1):
            user.chat_public_key = f"public-key-{index}"
            user.chat_key_algorithm = "RSA-OAEP-256"
            user.chat_key_version = 1
            user.chat_private_key_backup = f"encrypted-private-key-{index}"
            user.chat_private_key_backup_iv = f"backup-iv-{index}"
            user.chat_private_key_backup_salt = f"backup-salt-{index}"
            user.chat_private_key_backup_kdf = "PBKDF2-SHA256"
            user.chat_private_key_backup_kdf_iterations = 600000
            user.chat_private_key_backup_cipher = "AES-GCM"
            user.chat_private_key_backup_version = 1
            user.save(
                update_fields=[
                    "chat_public_key",
                    "chat_key_algorithm",
                    "chat_key_version",
                    "chat_private_key_backup",
                    "chat_private_key_backup_iv",
                    "chat_private_key_backup_salt",
                    "chat_private_key_backup_kdf",
                    "chat_private_key_backup_kdf_iterations",
                    "chat_private_key_backup_cipher",
                    "chat_private_key_backup_version",
                ]
            )


class BookingChatApiTests(BookingChatBaseMixin, APITestCase):
    def setUp(self):
        self.create_users()
        self.listing = self.create_listing()
        self.pending_booking = self.create_booking(guest=self.guest)
        self.confirmed_booking = self.create_booking(
            guest=self.guest,
            status=Booking.Status.CONFIRMED,
        )

    def test_guest_can_bootstrap_chat_for_pending_booking(self):
        self.client.force_authenticate(user=self.guest)

        response = self.client.get(
            reverse("booking-conversation", args=[self.pending_booking.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_chat_available"])
        self.assertEqual(len(response.data["participants"]), 2)
        self.assertEqual(
            {participant["id"] for participant in response.data["participants"]},
            {str(self.host.id), str(self.guest.id)},
        )
        self.assertTrue(
            all(participant["chat_encryption"] for participant in response.data["participants"])
        )
        self.assertNotIn("encrypted_private_key", response.data["participants"][0])

    def test_host_can_bootstrap_chat_for_confirmed_booking(self):
        self.client.force_authenticate(user=self.host)

        response = self.client.get(
            reverse("booking-conversation", args=[self.confirmed_booking.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["booking_status"], Booking.Status.CONFIRMED)

    def test_unrelated_user_cannot_open_booking_chat(self):
        self.client.force_authenticate(user=self.stranger)

        response = self.client.get(
            reverse("booking-conversation", args=[self.pending_booking.id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancelled_booking_chat_is_rejected(self):
        self.pending_booking.status = Booking.Status.CANCELLED_BY_GUEST
        self.pending_booking.save(update_fields=["status"])
        self.client.force_authenticate(user=self.guest)

        response = self.client.get(
            reverse("booking-conversation", args=[self.pending_booking.id])
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Chat is unavailable for this booking.")

    def test_attachment_upload_is_rejected_for_inactive_booking(self):
        conversation = get_or_create_conversation_for_booking(self.pending_booking)
        self.pending_booking.status = Booking.Status.CANCELLED_BY_HOST
        self.pending_booking.save(update_fields=["status"])
        self.client.force_authenticate(user=self.guest)

        response = self.client.post(
            reverse("conversation-attachments", args=[conversation.id]),
            {"file": SimpleUploadedFile("note.pdf", b"hello", content_type="application/pdf")},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Chat is unavailable for this booking.")


class BookingChatWebSocketTests(BookingChatBaseMixin, TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.create_users()
        self.listing = self.create_listing()

    def _token_for(self, user) -> str:
        return str(RefreshToken.for_user(user).access_token)

    def test_guest_can_send_message_over_websocket_for_pending_booking(self):
        booking = self.create_booking(guest=self.guest)
        conversation = get_or_create_conversation_for_booking(booking)
        encrypted_body = self.encrypted_body_for(
            guest_id=str(self.guest.id),
            host_id=str(self.host.id),
        )

        async def run_test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/messaging/conversations/{conversation.id}/?token={self._token_for(self.guest)}",
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to(
                {
                    "action": "message.send",
                    "payload": {
                        "body": "",
                        "encrypted_body": encrypted_body,
                    },
                }
            )
            response = await communicator.receive_json_from(timeout=5)

            self.assertEqual(response["type"], "message.created")
            self.assertEqual(response["message"]["body"], "")
            self.assertTrue(response["message"]["is_encrypted"])
            self.assertEqual(
                response["message"]["encrypted_body"]["ciphertext"],
                encrypted_body["ciphertext"],
            )
            self.assertEqual(response["message"]["sender"]["id"], str(self.guest.id))
            await communicator.disconnect()

        async_to_sync(run_test)()
        self.assertEqual(Message.objects.count(), 1)

    def test_host_can_send_message_over_websocket_for_confirmed_booking(self):
        booking = self.create_booking(
            guest=self.guest,
            status=Booking.Status.CONFIRMED,
        )
        conversation = get_or_create_conversation_for_booking(booking)
        encrypted_body = self.encrypted_body_for(
            guest_id=str(self.guest.id),
            host_id=str(self.host.id),
        )

        async def run_test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/messaging/conversations/{conversation.id}/?token={self._token_for(self.host)}",
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to(
                {
                    "action": "message.send",
                    "payload": {
                        "body": "",
                        "encrypted_body": encrypted_body,
                    },
                }
            )
            response = await communicator.receive_json_from(timeout=5)

            self.assertEqual(response["type"], "message.created")
            self.assertEqual(response["message"]["body"], "")
            self.assertTrue(response["message"]["is_encrypted"])
            self.assertEqual(response["message"]["sender"]["id"], str(self.host.id))
            await communicator.disconnect()

        async_to_sync(run_test)()

    def test_plaintext_text_message_is_rejected_over_websocket(self):
        booking = self.create_booking(guest=self.guest)
        conversation = get_or_create_conversation_for_booking(booking)

        async def run_test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/messaging/conversations/{conversation.id}/?token={self._token_for(self.guest)}",
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to(
                {"action": "message.send", "payload": {"body": "Hello host"}}
            )
            response = await communicator.receive_json_from(timeout=5)

            self.assertEqual(response["type"], "error")
            self.assertEqual(response["detail"], "Text messages must be end-to-end encrypted.")
            await communicator.disconnect()

        async_to_sync(run_test)()

    def test_encrypted_attachment_url_is_not_stored_in_plaintext_fields(self):
        booking = self.create_booking(guest=self.guest)
        conversation = get_or_create_conversation_for_booking(booking)
        encrypted_body = self.encrypted_body_for(
            guest_id=str(self.guest.id),
            host_id=str(self.host.id),
        )

        async def run_test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/messaging/conversations/{conversation.id}/?token={self._token_for(self.guest)}",
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to(
                {
                    "action": "message.send",
                    "payload": {
                        "body": "",
                        "encrypted_body": encrypted_body,
                        "message_type": "file",
                    },
                }
            )
            response = await communicator.receive_json_from(timeout=5)

            self.assertEqual(response["type"], "message.created")
            self.assertEqual(response["message"]["attachment_url"], "")
            self.assertEqual(response["message"]["attachment_name"], "")
            self.assertEqual(response["message"]["attachment_mime"], "")
            await communicator.disconnect()

        async_to_sync(run_test)()

        message = Message.objects.get()
        self.assertEqual(message.attachment_url, "")
        self.assertEqual(message.attachment_name, "")
        self.assertEqual(message.attachment_mime, "")
        self.assertIsNone(message.attachment_bytes)

    def test_inactive_booking_socket_connection_is_denied(self):
        booking = self.create_booking(
            guest=self.guest,
            status=Booking.Status.CANCELLED_BY_GUEST,
        )
        conversation = get_or_create_conversation_for_booking(booking)

        async def run_test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/messaging/conversations/{conversation.id}/?token={self._token_for(self.guest)}",
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        async_to_sync(run_test)()
