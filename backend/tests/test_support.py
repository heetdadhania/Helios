"""
Tests for Support Messages & Update Requests module (app/schemas/support.py,
app/repositories/support_repository.py, app/services/support_service.py, and app/api/support.py).
"""

from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.support_repository import SupportRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.support import SupportMessageCreate, SupportMessageOut
from app.services.support_service import SupportService


class TestSupportSchemas(unittest.TestCase):
    """Test validation and initialization of Support schemas."""

    def test_support_message_create_valid(self):
        payload = SupportMessageCreate(message="Can you please check batch #401?")
        self.assertEqual(payload.message, "Can you please check batch #401?")

    def test_support_message_out(self):
        now = datetime.now(timezone.utc)
        item = SupportMessageOut(
            message_id=1,
            tenant_id=10,
            tenant_name="Acme Corp",
            from_user_id=5,
            from_user_name="John Owner",
            to_user_id=20,
            to_user_name="Alice Support",
            message="Status inquiry",
            status="open",
            created_at=now,
            resolved_at=None,
        )
        self.assertEqual(item.message_id, 1)
        self.assertEqual(item.to_user_id, 20)
        self.assertEqual(item.status, "open")


class TestSupportRepository(unittest.TestCase):
    """Test SQL query construction and routing logic in SupportRepository."""

    def setUp(self):
        self.mock_cursor = MagicMock()
        self.repo = SupportRepository(self.mock_cursor, catalog="helios")

    def test_resolve_recipient_assigned_team_member(self):
        # Found assigned team member
        self.mock_cursor.description = [("user_id",)]
        self.mock_cursor.fetchone.return_value = (42,)

        recipient_id = self.repo.resolve_recipient_user_id(tenant_id=7)
        self.assertEqual(recipient_id, 42)

        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("team_assignments", sql)
        self.assertEqual(params["tenant_id"], 7)

    def test_resolve_recipient_fallback_to_admin(self):
        # 1. No assigned team member (None)
        # 2. Fallback to active admin (user_id = 99)
        self.mock_cursor.description = [("user_id",)]
        self.mock_cursor.fetchone.side_effect = [None, (99,)]

        recipient_id = self.repo.resolve_recipient_user_id(tenant_id=7)
        self.assertEqual(recipient_id, 99)

        # Verify second query searched for admin
        calls = self.mock_cursor.execute.call_args_list
        self.assertEqual(len(calls), 2)
        admin_sql = calls[1][0][0]
        self.assertIn("role", admin_sql.lower())
        self.assertIn("admin", admin_sql.lower())

    def test_get_messages_team_member_scoping(self):
        self.mock_cursor.description = [
            ("message_id",),
            ("tenant_id",),
            ("tenant_name",),
            ("from_user_id",),
            ("from_user_name",),
            ("to_user_id",),
            ("to_user_name",),
            ("message",),
            ("status",),
            ("created_at",),
            ("resolved_at",),
        ]
        self.mock_cursor.fetchall.return_value = []

        self.repo.get_messages(user_id=25, user_role="team_member", status_filter="open")

        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("to_user_id = :user_id", sql)
        self.assertEqual(params["user_id"], 25)
        self.assertEqual(params["status_filter"], "open")

    def test_get_messages_admin_all(self):
        self.mock_cursor.description = [
            ("message_id",),
            ("tenant_id",),
            ("tenant_name",),
            ("from_user_id",),
            ("from_user_name",),
            ("to_user_id",),
            ("to_user_name",),
            ("message",),
            ("status",),
            ("created_at",),
            ("resolved_at",),
        ]
        self.mock_cursor.fetchall.return_value = []

        self.repo.get_messages(user_id=1, user_role="admin")

        args = self.mock_cursor.execute.call_args[0]
        sql = args[0]
        self.assertNotIn("to_user_id = :user_id", sql)


class TestSupportEndpoints(unittest.TestCase):
    """Test API endpoint authorization, routing, and response serialization."""

    def setUp(self):
        self.client = TestClient(app)
        self.smb_user = UserOut(
            id=10,
            name="Bob Owner",
            email="bob@owner.com",
            role=UserRole.SMB_OWNER,
            tenant_id=5,
        )
        self.team_user = UserOut(
            id=20,
            name="Charlie Support",
            email="charlie@helios.internal",
            role=UserRole.TEAM_MEMBER,
            tenant_id=None,
        )
        self.admin_user = UserOut(
            id=30,
            name="Diana Admin",
            email="diana@helios.internal",
            role=UserRole.ADMIN,
            tenant_id=None,
        )

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_endpoints_require_auth(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        res_post = self.client.post("/api/support/messages", json={"message": "Hello"})
        self.assertEqual(res_post.status_code, 401)

        res_get = self.client.get("/api/support/messages")
        self.assertEqual(res_get.status_code, 401)

        res_res = self.client.post("/api/support/messages/1/resolve")
        self.assertEqual(res_res.status_code, 401)

    def test_create_message_smb_owner_only(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        # Team Member forbidden from posting
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        res_tm = self.client.post("/api/support/messages", json={"message": "Inquiry"})
        self.assertEqual(res_tm.status_code, 403)

        # SMB Owner allowed
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        mock_msg = SupportMessageOut(
            message_id=1,
            tenant_id=5,
            tenant_name="Bob Store",
            from_user_id=10,
            from_user_name="Bob Owner",
            to_user_id=20,
            to_user_name="Charlie Support",
            message="Please check latest upload",
            status="open",
            created_at=datetime.now(timezone.utc),
            resolved_at=None,
        )
        with patch.object(SupportService, "send_message", return_value=mock_msg):
            res_smb = self.client.post("/api/support/messages", json={"message": "Please check latest upload"})
            self.assertEqual(res_smb.status_code, 201)
            data = res_smb.json()
            self.assertEqual(data["message_id"], 1)
            self.assertEqual(data["to_user_id"], 20)
            self.assertEqual(data["status"], "open")

    def test_get_messages_team_and_admin_allowed(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        # SMB Owner forbidden
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        res_smb = self.client.get("/api/support/messages")
        self.assertEqual(res_smb.status_code, 403)

        # Team Member allowed
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        with patch.object(SupportService, "get_messages", return_value=[]):
            res_tm = self.client.get("/api/support/messages")
            self.assertEqual(res_tm.status_code, 200)

        # Admin allowed
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        with patch.object(SupportService, "get_messages", return_value=[]):
            res_adm = self.client.get("/api/support/messages")
            self.assertEqual(res_adm.status_code, 200)

    def test_resolve_message_endpoint(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        app.dependency_overrides[get_current_user] = lambda: self.team_user

        from app.schemas.support import SupportMessageResolveResponse
        mock_resp = SupportMessageResolveResponse(
            success=True,
            message="Support message marked as resolved.",
            message_id=5,
            status="resolved",
            resolved_at=datetime.now(timezone.utc),
        )
        with patch.object(SupportService, "resolve_message", return_value=mock_resp):
            res = self.client.post("/api/support/messages/5/resolve")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["status"], "resolved")


if __name__ == "__main__":
    unittest.main()
