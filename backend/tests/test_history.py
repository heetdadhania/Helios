"""
Tests for Data Submission History module (app/schemas/history.py,
app/repositories/history_repository.py, and app/api/history.py).
"""

from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.history_repository import HistoryRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.history import AdminHistoryOut, SmbHistoryOut, TeamHistoryOut


class TestHistorySchemas(unittest.TestCase):
    """Test validation and initialization of History Pydantic schemas."""

    def test_smb_history_schema(self):
        item = SmbHistoryOut(
            batch_id="batch-123",
            date="2024-03-28 14:00:00",
            status="Ready",
            label="Data received",
        )
        self.assertEqual(item.batch_id, "batch-123")
        self.assertEqual(item.status, "Ready")
        self.assertEqual(item.label, "Data received")

    def test_team_history_schema(self):
        now = datetime.now(timezone.utc)
        item = TeamHistoryOut(
            batch_id="batch-456",
            tenant_id=1,
            tenant="Acme Retail",
            source_type="upload",
            stage="silver_clean",
            status="silver_running",
            error_message=None,
            timestamp=now,
        )
        self.assertEqual(item.tenant, "Acme Retail")
        self.assertEqual(item.stage, "silver_clean")
        self.assertIsNone(item.error_message)

    def test_admin_history_schema(self):
        now = datetime.now(timezone.utc)
        item = AdminHistoryOut(
            batch_id="batch-789",
            tenant_id=2,
            tenant="Beta Logistics",
            source_type="db_connection",
            stage="gold_transform",
            status="success",
            error_message=None,
            timestamp=now,
            handled_by="Alice Support",
        )
        self.assertEqual(item.handled_by, "Alice Support")
        self.assertEqual(item.status, "success")


class TestHistoryRepository(unittest.TestCase):
    """Test SQL query construction and response mapping in HistoryRepository."""

    def setUp(self):
        self.mock_cursor = MagicMock()
        self.repo = HistoryRepository(self.mock_cursor, catalog="helios")

    def test_get_smb_history_status_mapping(self):
        self.mock_cursor.description = [
            ("batch_id",),
            ("status",),
            ("stage",),
            ("created_at",),
        ]
        test_dt = datetime(2024, 3, 28, 12, 0, 0)
        self.mock_cursor.fetchall.return_value = [
            ("b-1", "success", "gold_transform", test_dt),
            ("b-2", "silver_running", "silver_clean", test_dt),
            ("b-3", "failed", "bronze_ingest", test_dt),
        ]

        results = self.repo.get_smb_history(tenant_id=10)
        self.assertEqual(len(results), 3)

        # 1. Success maps to 'Ready'
        self.assertEqual(results[0]["status"], "Ready")
        self.assertEqual(results[0]["label"], "Data received")
        self.assertEqual(results[0]["date"], "2024-03-28 12:00:00")

        # 2. In-flight maps to 'Processing'
        self.assertEqual(results[1]["status"], "Processing")

        # 3. Failed maps to 'Needs attention — please resend'
        self.assertEqual(results[2]["status"], "Needs attention — please resend")

        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("platform`.`pipeline_status", sql)
        self.assertEqual(params["tenant_id"], 10)

    def test_get_team_history_team_member_scoping(self):
        self.mock_cursor.description = [
            ("batch_id",),
            ("tenant_id",),
            ("tenant",),
            ("source_type",),
            ("stage",),
            ("status",),
            ("error_message",),
            ("timestamp",),
        ]
        self.mock_cursor.fetchall.return_value = []

        self.repo.get_team_history(
            user_id=20,
            user_role="team_member",
            status_filter="failed",
            tenant_filter="Acme",
        )

        sql, params = self.mock_cursor.execute.call_args[0]
        # Team Member must be scoped via team_assignments
        self.assertIn("team_assignments", sql)
        self.assertEqual(params["user_id"], 20)
        self.assertEqual(params["status_filter"], "failed")
        self.assertIn("%acme%", params["tenant_like"])

    def test_get_team_history_admin_all_tenants(self):
        self.mock_cursor.description = [
            ("batch_id",),
            ("tenant_id",),
            ("tenant",),
            ("source_type",),
            ("stage",),
            ("status",),
            ("error_message",),
            ("timestamp",),
        ]
        self.mock_cursor.fetchall.return_value = []

        self.repo.get_team_history(
            user_id=99,
            user_role="admin",
        )

        args = self.mock_cursor.execute.call_args[0]
        sql = args[0]
        # Admin is NOT constrained to team_assignments
        self.assertNotIn("user_id = :user_id", sql)

    def test_get_admin_history_handled_by(self):
        self.mock_cursor.description = [
            ("batch_id",),
            ("tenant_id",),
            ("tenant",),
            ("source_type",),
            ("stage",),
            ("status",),
            ("error_message",),
            ("timestamp",),
            ("handled_by",),
        ]
        test_dt = datetime(2024, 3, 28, 10, 0, 0)
        self.mock_cursor.fetchall.return_value = [
            ("b-1", 1, "Acme", "upload", "gold_transform", "success", None, test_dt, "Alice Support"),
            ("b-2", 2, "Beta", "api_push", "bronze_ingest", "failed", "Validation error", test_dt, "N/A"),
        ]

        results = self.repo.get_admin_history(status_filter="success")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["handled_by"], "Alice Support")
        self.assertEqual(results[1]["handled_by"], "N/A")

        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("handled_by", sql)
        self.assertEqual(params["status_filter"], "success")


class TestHistoryEndpoints(unittest.TestCase):
    """Test API endpoint authorization, routing, and response serialization."""

    def setUp(self):
        self.client = TestClient(app)
        self.smb_user = UserOut(
            id=1,
            name="Bob Owner",
            email="bob@owner.com",
            role=UserRole.SMB_OWNER,
            tenant_id=5,
        )
        self.team_user = UserOut(
            id=2,
            name="Charlie Support",
            email="charlie@helios.internal",
            role=UserRole.TEAM_MEMBER,
            tenant_id=None,
        )
        self.admin_user = UserOut(
            id=3,
            name="Diana Admin",
            email="diana@helios.internal",
            role=UserRole.ADMIN,
            tenant_id=None,
        )

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_endpoints_require_auth(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        endpoints = ["/api/history/mine", "/api/history/team", "/api/history/admin"]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 401, f"{ep} should require authentication")

    def test_mine_role_guards(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        # SMB Owner allowed
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        with patch.object(HistoryRepository, "get_smb_history", return_value=[]):
            res = self.client.get("/api/history/mine")
            self.assertEqual(res.status_code, 200)

        # Team Member forbidden
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        res = self.client.get("/api/history/mine")
        self.assertEqual(res.status_code, 403)

        # Admin forbidden
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        res = self.client.get("/api/history/mine")
        self.assertEqual(res.status_code, 403)

    def test_team_role_guards(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        # SMB Owner forbidden
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        res = self.client.get("/api/history/team")
        self.assertEqual(res.status_code, 403)

        # Team Member allowed
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        with patch.object(HistoryRepository, "get_team_history", return_value=[]):
            res = self.client.get("/api/history/team")
            self.assertEqual(res.status_code, 200)

        # Admin allowed
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        with patch.object(HistoryRepository, "get_team_history", return_value=[]):
            res = self.client.get("/api/history/team")
            self.assertEqual(res.status_code, 200)

    def test_admin_role_guards(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        # SMB Owner forbidden
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        res = self.client.get("/api/history/admin")
        self.assertEqual(res.status_code, 403)

        # Team Member forbidden
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        res = self.client.get("/api/history/admin")
        self.assertEqual(res.status_code, 403)

        # Admin allowed
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        with patch.object(HistoryRepository, "get_admin_history", return_value=[]):
            res = self.client.get("/api/history/admin")
            self.assertEqual(res.status_code, 200)

    def test_mine_success_payload(self):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_data = [
            {"batch_id": "b-1", "date": "2024-03-28 14:00:00", "status": "Ready", "label": "Data received"},
            {"batch_id": "b-2", "date": "2024-03-27 10:00:00", "status": "Needs attention — please resend", "label": "Data received"},
        ]
        with patch.object(HistoryRepository, "get_smb_history", return_value=mock_data):
            res = self.client.get("/api/history/mine")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["status"], "Ready")
            self.assertEqual(data[0]["label"], "Data received")
            self.assertNotIn("stage", data[0])
            self.assertNotIn("error_message", data[0])

    def test_team_success_payload_with_filters(self):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_data = [
            {
                "batch_id": "b-10",
                "tenant_id": 5,
                "tenant": "Acme Retail",
                "source_type": "upload",
                "stage": "silver_clean",
                "status": "failed",
                "error_message": "Row validation rejected",
                "timestamp": datetime(2024, 3, 28, 15, 0, 0, tzinfo=timezone.utc),
            }
        ]
        with patch.object(HistoryRepository, "get_team_history", return_value=mock_data) as mock_get:
            res = self.client.get("/api/history/team?status=failed&tenant=Acme")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["error_message"], "Row validation rejected")
            self.assertEqual(data[0]["stage"], "silver_clean")
            mock_get.assert_called_once_with(
                user_id=2,
                user_role="team_member",
                status_filter="failed",
                tenant_filter="Acme",
            )

    def test_admin_success_payload_handled_by(self):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_data = [
            {
                "batch_id": "b-20",
                "tenant_id": 6,
                "tenant": "Global Logistics",
                "source_type": "upload",
                "stage": "gold_transform",
                "status": "success",
                "error_message": None,
                "timestamp": datetime(2024, 3, 28, 16, 0, 0, tzinfo=timezone.utc),
                "handled_by": "Charlie Support",
            }
        ]
        with patch.object(HistoryRepository, "get_admin_history", return_value=mock_data) as mock_get:
            res = self.client.get("/api/history/admin")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["handled_by"], "Charlie Support")
            self.assertEqual(data[0]["tenant"], "Global Logistics")


if __name__ == "__main__":
    unittest.main()
