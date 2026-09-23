import json
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.confirmation_repository import ConfirmationRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.confirmation import (
    ConfirmRequest,
    ConfirmResponse,
    PendingUploadOut,
    SchemaPreviewOut,
)
from app.services.confirmation_service import ConfirmationService


class TestConfirmationSchemas(unittest.TestCase):
    """Test validation and default values of confirmation schemas."""

    def test_pending_upload_out_valid(self):
        item = PendingUploadOut(
            batch_id="batch-123",
            tenant_id=1,
            source_type="db_connection",
            detected_template="template_orders",
            confidence_score=0.85,
        )
        self.assertEqual(item.batch_id, "batch-123")
        self.assertEqual(item.tenant_id, 1)
        self.assertEqual(item.source_type, "db_connection")
        self.assertEqual(item.status, "awaiting_confirmation")
        self.assertEqual(item.stage, "schema_inference")

    def test_schema_preview_out_valid(self):
        preview = SchemaPreviewOut(
            batch_id="batch-preview",
            tenant_id=2,
            detected_template="template_shipping",
            confidence_score=0.92,
            source_type="api_push",
            column_mapping={"track_no": {"target_field": "tracking_number", "similarity_score": 90.0}},
            sample_rows=[{"track_no": "TRK12345", "carrier": "FedEx"}],
        )
        self.assertEqual(preview.batch_id, "batch-preview")
        self.assertEqual(preview.source_type, "api_push")
        self.assertEqual(len(preview.sample_rows), 1)

    def test_confirm_request_and_response(self):
        req = ConfirmRequest(
            confirmed_template="template_orders",
            corrected_mapping={"cust_id": {"target_field": "customer_id"}},
        )
        self.assertEqual(req.confirmed_template, "template_orders")
        self.assertIsNotNone(req.corrected_mapping)

        res = ConfirmResponse(
            batch_id="batch-456",
            confirmed_template="template_orders",
            message="Confirmed successfully",
        )
        self.assertEqual(res.status, "silver_running")


class TestConfirmationRepository(unittest.TestCase):
    """Test repository database query generation and logic."""

    def setUp(self):
        self.mock_cursor = MagicMock()
        self.repo = ConfirmationRepository(self.mock_cursor, catalog="helios")

    def test_get_pending_admin_sees_all(self):
        self.mock_cursor.description = [
            ("batch_id",),
            ("tenant_id",),
            ("upload_id",),
            ("stage",),
            ("status",),
            ("created_at",),
            ("updated_at",),
            ("detected_template",),
            ("confidence_score",),
            ("source_type",),
        ]
        self.mock_cursor.fetchall.return_value = [
            ("b1", 1, None, "schema_inference", "awaiting_confirmation", None, None, "template_orders", 0.95, "upload"),
            ("b2", 2, None, "schema_inference", "awaiting_confirmation", None, None, "template_shipping", 0.88, "api_push"),
        ]

        results = self.repo.get_pending(user_id=99, user_role="admin")
        self.assertEqual(len(results), 2)
        sql = self.mock_cursor.execute.call_args[0][0]
        self.assertNotIn("team_assignments", sql)

    def test_get_pending_team_member_filters_by_assignment(self):
        self.mock_cursor.description = [
            ("batch_id",),
            ("tenant_id",),
            ("upload_id",),
            ("stage",),
            ("status",),
            ("created_at",),
            ("updated_at",),
            ("detected_template",),
            ("confidence_score",),
            ("source_type",),
        ]
        self.mock_cursor.fetchall.return_value = [
            ("b1", 1, None, "schema_inference", "awaiting_confirmation", None, None, "template_orders", 0.95, "upload"),
        ]

        results = self.repo.get_pending(user_id=10, user_role="team_member")
        self.assertEqual(len(results), 1)
        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("team_assignments", sql)
        self.assertEqual(params["user_id"], 10)

    def test_check_user_tenant_access_admin_and_team(self):
        # Admin is always permitted
        self.assertTrue(self.repo.check_user_tenant_access(user_id=1, user_role="admin", tenant_id=100))

        # SMB Owner is never permitted
        self.assertFalse(self.repo.check_user_tenant_access(user_id=2, user_role="smb_owner", tenant_id=100))

        # Team member with assignment
        self.mock_cursor.fetchone.return_value = (1,)
        self.assertTrue(self.repo.check_user_tenant_access(user_id=3, user_role="team_member", tenant_id=100))

        # Team member without assignment
        self.mock_cursor.fetchone.return_value = None
        self.assertFalse(self.repo.check_user_tenant_access(user_id=4, user_role="team_member", tenant_id=100))

    def test_save_confirmation(self):
        self.repo.save_confirmation(
            batch_id="batch-save",
            confirmed_template="template_orders",
            column_mapping={"order_num": {"target_field": "order_id"}},
            confirmed_by=55,
        )
        self.assertGreaterEqual(self.mock_cursor.execute.call_count, 2)
        # Check updates to inferred_schema and pipeline_status
        executed_sqls = [call[0][0] for call in self.mock_cursor.execute.call_args_list]
        self.assertTrue(any("inferred_schema" in sql for sql in executed_sqls))
        self.assertTrue(any("pipeline_status" in sql and "silver_running" in sql for sql in executed_sqls))


class TestConfirmationService(unittest.TestCase):
    """Test business logic and authorization enforcement in ConfirmationService."""

    def setUp(self):
        self.mock_repo = MagicMock(spec=ConfirmationRepository)
        self.team_user = UserOut(
            id=10,
            name="Alice Support",
            email="alice@helios.internal",
            role=UserRole.TEAM_MEMBER,
            tenant_id=None,
        )

    def test_get_preview_not_found(self):
        self.mock_repo.get_batch_metadata.return_value = None
        with self.assertRaises(Exception) as cm:
            ConfirmationService.get_preview("batch-none", self.team_user, self.mock_repo)
        self.assertEqual(cm.exception.status_code, 404)

    def test_get_preview_forbidden_tenant(self):
        self.mock_repo.get_batch_metadata.return_value = {"tenant_id": 99}
        self.mock_repo.check_user_tenant_access.return_value = False

        with self.assertRaises(Exception) as cm:
            ConfirmationService.get_preview("batch-unassigned", self.team_user, self.mock_repo)
        self.assertEqual(cm.exception.status_code, 403)

    def test_confirm_mapping_rejects_wrong_status(self):
        self.mock_repo.get_batch_metadata.return_value = {
            "tenant_id": 1,
            "status": "silver_running",  # already running
        }
        self.mock_repo.check_user_tenant_access.return_value = True

        req = ConfirmRequest(confirmed_template="template_orders")
        with self.assertRaises(Exception) as cm:
            ConfirmationService.confirm_mapping("batch-running", req, self.team_user, self.mock_repo)
        self.assertEqual(cm.exception.status_code, 400)

    @patch("app.services.confirmation_service.trigger_silver_stage")
    def test_confirm_mapping_success(self, mock_trigger):
        self.mock_repo.get_batch_metadata.return_value = {
            "batch_id": "batch-ok",
            "tenant_id": 5,
            "status": "awaiting_confirmation",
            "column_mapping_json": json.dumps({"ord_id": {"target_field": "order_id"}}),
        }
        self.mock_repo.check_user_tenant_access.return_value = True

        req = ConfirmRequest(
            confirmed_template="template_orders",
            corrected_mapping={"cust_email": {"target_field": "customer_email"}},
        )

        res = ConfirmationService.confirm_mapping("batch-ok", req, self.team_user, self.mock_repo)

        self.assertEqual(res.status, "silver_running")
        self.assertEqual(res.confirmed_template, "template_orders")
        self.mock_repo.save_confirmation.assert_called_once()
        mock_trigger.assert_called_once()


class TestConfirmationEndpoints(unittest.TestCase):
    """Test API endpoints, authentication, and RBAC."""

    def setUp(self):
        self.client = TestClient(app)
        self.admin_user = UserOut(
            id=1,
            name="Admin User",
            email="admin@helios.internal",
            role=UserRole.ADMIN,
            tenant_id=None,
        )
        self.team_user = UserOut(
            id=2,
            name="Team User",
            email="team@helios.internal",
            role=UserRole.TEAM_MEMBER,
            tenant_id=None,
        )
        self.smb_user = UserOut(
            id=3,
            name="SMB Owner",
            email="owner@acme.com",
            role=UserRole.SMB_OWNER,
            tenant_id=10,
        )

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_endpoints_require_auth(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        # Without auth credentials, should return 401
        res = self.client.get("/api/uploads/pending")
        self.assertEqual(res.status_code, 401)

        res = self.client.get("/api/uploads/batch-1/preview")
        self.assertEqual(res.status_code, 401)

        res = self.client.post("/api/uploads/batch-1/confirm", json={"confirmed_template": "template_orders"})
        self.assertEqual(res.status_code, 401)

    def test_smb_owner_forbidden_from_confirmation_endpoints(self):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        # SMB Owners must receive 403 Forbidden
        res = self.client.get("/api/uploads/pending")
        self.assertEqual(res.status_code, 403)

        res = self.client.get("/api/uploads/batch-1/preview")
        self.assertEqual(res.status_code, 403)

        res = self.client.post("/api/uploads/batch-1/confirm", json={"confirmed_template": "template_orders"})
        self.assertEqual(res.status_code, 403)

    @patch.object(ConfirmationService, "get_pending_uploads")
    def test_get_pending_team_member_success(self, mock_service):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_service.return_value = [
            PendingUploadOut(
                batch_id="batch-001",
                tenant_id=10,
                source_type="upload",
                detected_template="template_orders",
                confidence_score=0.91,
            )
        ]

        res = self.client.get("/api/uploads/pending")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["batch_id"], "batch-001")
        self.assertEqual(data[0]["source_type"], "upload")

    @patch.object(ConfirmationService, "get_preview")
    def test_get_preview_admin_success(self, mock_service):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_service.return_value = SchemaPreviewOut(
            batch_id="batch-002",
            tenant_id=12,
            detected_template="template_shipping",
            confidence_score=0.88,
            source_type="db_connection",
            column_mapping={"tracking": {"target_field": "tracking_number"}},
            sample_rows=[{"tracking": "TRK-999"}],
        )

        res = self.client.get("/api/uploads/batch-002/preview")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["batch_id"], "batch-002")
        self.assertEqual(data["detected_template"], "template_shipping")
        self.assertEqual(data["source_type"], "db_connection")
        self.assertEqual(len(data["sample_rows"]), 1)

    @patch.object(ConfirmationService, "confirm_mapping")
    def test_post_confirm_success(self, mock_confirm):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_confirm.return_value = ConfirmResponse(
            batch_id="batch-003",
            status="silver_running",
            confirmed_template="template_orders",
            message="Batch confirmed successfully.",
        )

        res = self.client.post(
            "/api/uploads/batch-003/confirm",
            json={"confirmed_template": "template_orders"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["batch_id"], "batch-003")
        self.assertEqual(data["status"], "silver_running")


if __name__ == "__main__":
    unittest.main()
