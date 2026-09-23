import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.notification_repository import NotificationRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.notification import (
    NotificationCreate,
    NotificationOut,
    NotificationReadResponse,
    NotificationType,
)
from app.services.notification_service import NotificationService


class TestNotificationSchemas(unittest.TestCase):
    """Test validation and defaults for notification schemas."""

    def test_notification_out_serialization(self):
        notif = NotificationOut(
            notification_id=42,
            tenant_id=1,
            user_id=10,
            message="Your data is being processed",
            type="info",
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        self.assertEqual(notif.notification_id, 42)
        self.assertEqual(notif.message, "Your data is being processed")
        self.assertFalse(notif.is_read)

    def test_notification_read_response(self):
        resp = NotificationReadResponse(
            notification_id=42,
            is_read=True,
        )
        self.assertEqual(resp.notification_id, 42)
        self.assertTrue(resp.is_read)


class TestNotificationServiceTriggers(unittest.TestCase):
    """Test the trigger points implemented across causing services."""

    def setUp(self):
        self.mock_cursor = MagicMock()
        self.mock_cursor.description = [("notification_id",), ("tenant_id",), ("user_id",), ("message",), ("type",), ("is_read",), ("created_at",)]
        self.mock_cursor.fetchall.return_value = [
            (101, 1, 5, "Your data is being processed", "info", False, datetime.now(timezone.utc))
        ]

    def test_notify_upload_received(self):
        with patch.object(NotificationRepository, "create") as mock_create:
            mock_create.return_value = {
                "notification_id": 1,
                "tenant_id": 1,
                "user_id": 5,
                "message": "Your data is being processed",
                "type": "info",
                "is_read": False,
            }
            res = NotificationService.notify_upload_received(
                tenant_id=1,
                batch_id="batch-test-123",
                user_id=5,
                source_type="upload",
                cursor=self.mock_cursor,
            )
            self.assertIsNotNone(res)
            mock_create.assert_called_once_with(
                tenant_id=1,
                user_id=5,
                message="Your data is being processed",
                type=NotificationType.INFO.value,
            )

    def test_notify_pipeline_failed(self):
        with patch.object(NotificationRepository, "create") as mock_create:
            mock_create.return_value = {
                "notification_id": 2,
                "tenant_id": 1,
                "user_id": None,
                "message": "Pipeline failure at stage 'silver_clean' for batch 'batch-abc'",
                "type": "error",
                "is_read": False,
            }
            res = NotificationService.notify_pipeline_failed(
                tenant_id=1,
                batch_id="batch-abc",
                stage="silver_clean",
                error_message="Currency parse error",
                cursor=self.mock_cursor,
            )
            self.assertIsNotNone(res)
            mock_create.assert_called_once()
            args, kwargs = mock_create.call_args
            self.assertIn("Pipeline failure at stage 'silver_clean'", kwargs["message"])
            self.assertEqual(kwargs["type"], NotificationType.ERROR.value)

    def test_notify_dashboard_ready(self):
        with patch.object(NotificationRepository, "create") as mock_create:
            mock_create.return_value = {
                "notification_id": 3,
                "tenant_id": 1,
                "user_id": 5,
                "message": "Your dashboard is ready to view",
                "type": "pipeline_success",
                "is_read": False,
            }
            res = NotificationService.notify_dashboard_ready(
                tenant_id=1,
                batch_id="batch-gold-999",
                user_id=5,
                cursor=self.mock_cursor,
            )
            self.assertIsNotNone(res)
            mock_create.assert_called_once_with(
                tenant_id=1,
                user_id=5,
                message="Your dashboard is ready to view",
                type=NotificationType.PIPELINE_SUCCESS.value,
            )

    def test_notify_restart_required(self):
        with patch.object(NotificationRepository, "create") as mock_create:
            mock_create.return_value = {
                "notification_id": 4,
                "tenant_id": 1,
                "user_id": 5,
                "message": "Please re-upload your data — we need a fresh copy to continue processing",
                "type": "warning",
                "is_read": False,
            }
            res = NotificationService.notify_restart_required(
                tenant_id=1,
                batch_id="batch-corrupt-001",
                user_id=5,
                cursor=self.mock_cursor,
            )
            self.assertIsNotNone(res)
            mock_create.assert_called_once_with(
                tenant_id=1,
                user_id=5,
                message="Please re-upload your data — we need a fresh copy to continue processing",
                type=NotificationType.WARNING.value,
            )


class TestNotificationEndpoints(unittest.TestCase):
    """Test GET /api/notifications and POST /api/notifications/{id}/read."""

    def setUp(self):
        self.client = TestClient(app)
        self.mock_cursor = MagicMock()
        self.mock_cursor.description = [("notification_id",), ("tenant_id",), ("user_id",), ("message",), ("type",), ("is_read",), ("created_at",)]
        self.mock_cursor.fetchall.return_value = [
            (1, 1, 10, "Your data is being processed", "info", False, datetime.now(timezone.utc)),
            (2, 1, 10, "Your dashboard is ready to view", "pipeline_success", False, datetime.now(timezone.utc)),
        ]

        self.smb_user = UserOut(
            id=10,
            email="owner@store.com",
            name="Store Owner",
            role=UserRole.SMB_OWNER,
            tenant_id=1,
            is_active=True,
        )

        self.admin_user = UserOut(
            id=1,
            email="admin@helios.io",
            name="Admin User",
            role=UserRole.ADMIN,
            tenant_id=None,
            is_active=True,
        )

    def test_get_notifications_smb_owner(self):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: self.mock_cursor

        try:
            response = self.client.get("/api/notifications?unread_only=false")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["message"], "Your data is being processed")
            self.assertEqual(data[1]["message"], "Your dashboard is ready to view")
        finally:
            app.dependency_overrides.clear()

    def test_post_notification_read_success(self):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: self.mock_cursor

        with patch.object(NotificationRepository, "get_by_id") as mock_get_by_id, \
             patch.object(NotificationRepository, "mark_as_read") as mock_mark_read:
            mock_get_by_id.return_value = {
                "notification_id": 1,
                "tenant_id": 1,
                "user_id": 10,
                "message": "Your data is being processed",
                "type": "info",
                "is_read": False,
            }
            mock_mark_read.return_value = True

            try:
                response = self.client.post("/api/notifications/1/read")
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertEqual(result["notification_id"], 1)
                self.assertTrue(result["is_read"])
            finally:
                app.dependency_overrides.clear()

    def test_post_notification_read_not_found(self):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: self.mock_cursor

        with patch.object(NotificationRepository, "mark_as_read") as mock_mark_read:
            mock_mark_read.return_value = False

            try:
                response = self.client.post("/api/notifications/9999/read")
                self.assertEqual(response.status_code, 404)
            finally:
                app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
