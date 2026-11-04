"""
Unit tests validating server-side pagination across all 8 endpoints:
1. Pending Uploads (/api/v1/uploads/pending)
2. Submission History (/api/v1/history/mine, /api/v1/history/team, /api/v1/history/admin)
3. Pipeline Runs (/api/v1/pipeline/runs)
4. Data Quality (/api/v1/quality/logs)
5. Organizations / Tenants (/api/v1/tenants)
6. Team Members (/api/v1/team-members)
7. Support Messages (/api/v1/support/messages)
8. Notifications (/api/v1/notifications)
"""

import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.schemas.auth import UserOut, UserRole
from app.schemas.common import PaginatedResponse


class TestPaginationAllEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.admin_user = UserOut(
            id=1,
            name="Admin User",
            email="admin@helios.com",
            role=UserRole.ADMIN,
            tenant_id=None,
        )
        self.team_user = UserOut(
            id=2,
            name="Team Member",
            email="team@helios.com",
            role=UserRole.TEAM_MEMBER,
            tenant_id=None,
        )
        self.smb_user = UserOut(
            id=3,
            name="Owner User",
            email="owner@tenant.com",
            role=UserRole.SMB_OWNER,
            tenant_id=10,
        )

    def tearDown(self):
        app.dependency_overrides.clear()

    # 1. Pending Uploads
    @patch("app.repositories.confirmation_repository.ConfirmationRepository.get_pending")
    def test_pending_uploads_pagination(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_repo.return_value = (
            [
                {
                    "batch_id": f"batch-{i}",
                    "tenant_id": 10,
                    "tenant_name": "Acme",
                    "upload_id": i,
                    "stage": "schema_inference",
                    "status": "awaiting_confirmation",
                    "detected_template": "template_orders",
                    "confidence_score": 0.95,
                    "source_type": "upload",
                    "filename": f"file_{i}.csv",
                    "created_at": None,
                    "updated_at": None,
                }
                for i in range(2)
            ],
            45,
        )

        res = self.client.get("/api/v1/uploads/pending?page=2&page_size=2")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["page_size"], 2)
        self.assertEqual(data["total"], 45)
        self.assertEqual(len(data["items"]), 2)

        # Max page_size > 100 rejected
        bad_res = self.client.get("/api/v1/uploads/pending?page_size=101")
        self.assertEqual(bad_res.status_code, 422)

    # 2. Submission History (all roles)
    @patch("app.repositories.history_repository.HistoryRepository.get_smb_history")
    def test_smb_history_pagination(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_repo.return_value = (
            [{"batch_id": "b-1", "date": "2024-03-28", "status": "Ready", "label": "Data received"}],
            50,
        )

        res = self.client.get("/api/v1/history/mine?page=3&page_size=1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 3)
        self.assertEqual(data["page_size"], 1)
        self.assertEqual(data["total"], 50)
        self.assertEqual(len(data["items"]), 1)

    @patch("app.repositories.history_repository.HistoryRepository.get_team_history")
    def test_team_history_pagination(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_repo.return_value = (
            [
                {
                    "batch_id": "b-2",
                    "tenant_id": 5,
                    "tenant": "Client 5",
                    "source_type": "upload",
                    "stage": "silver_clean",
                    "status": "success",
                    "error_message": None,
                    "timestamp": "2024-03-28 10:00:00",
                }
            ],
            60,
        )

        res = self.client.get("/api/v1/history/team?page=2&page_size=10")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["page_size"], 10)
        self.assertEqual(data["total"], 60)
        self.assertEqual(len(data["items"]), 1)

    @patch("app.repositories.history_repository.HistoryRepository.get_admin_history")
    def test_admin_history_pagination(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_repo.return_value = (
            [
                {
                    "batch_id": "b-3",
                    "tenant_id": 7,
                    "tenant": "Client 7",
                    "source_type": "upload",
                    "stage": "gold_transform",
                    "status": "success",
                    "error_message": None,
                    "timestamp": "2024-03-28 12:00:00",
                    "handled_by": "Support Member",
                }
            ],
            75,
        )

        res = self.client.get("/api/v1/history/admin?page=1&page_size=20")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 20)
        self.assertEqual(data["total"], 75)
        self.assertEqual(len(data["items"]), 1)

    # 3. Pipeline Runs
    @patch("app.repositories.pipeline_health_repository.PipelineHealthRepository.list_runs")
    def test_pipeline_runs_pagination(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_repo.return_value = (
            [
                {
                    "batch_id": "b-run-1",
                    "tenant_id": 5,
                    "tenant": "Client 5",
                    "tenant_name": "Client 5",
                    "source_type": "upload",
                    "current_stage": "gold_transform",
                    "status": "success",
                    "started_at": "2024-03-28 10:00:00",
                    "updated_at": "2024-03-28 10:05:00",
                    "error_message": None,
                }
            ],
            42,
        )

        res = self.client.get("/api/v1/pipeline/runs?page=2&page_size=5")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["page_size"], 5)
        self.assertEqual(data["total"], 42)
        self.assertEqual(len(data["items"]), 1)

    # 4. Data Quality
    @patch("app.repositories.data_quality_repository.DataQualityRepository.list_logs")
    def test_data_quality_pagination(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_repo.return_value = (
            [
                {
                    "id": "dql-1",
                    "batch_id": "b-dq-1",
                    "tenant_id": "1",
                    "tenant_name": "Client 1",
                    "table_name": "bronze.raw_orders",
                    "rejection_reason": "Order null rate exceeded",
                    "timestamp": "2024-03-28T10:00:00",
                    "error_category": "Null Threshold Exceeded",
                }
            ],
            100,
        )

        res = self.client.get("/api/v1/quality/logs?page=3&page_size=15")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 3)
        self.assertEqual(data["page_size"], 15)
        self.assertEqual(data["total"], 100)
        self.assertEqual(len(data["items"]), 1)

    # 5. Organizations (Tenants)
    @patch("app.repositories.tenant_repository.TenantRepository.list_for_user")
    def test_tenants_pagination(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_repo.return_value = (
            [
                {
                    "tenant_id": 1,
                    "business_name": "Tata Consumer",
                    "contact_email": "tata@example.com",
                    "contact_person_name": "Tata Rep",
                    "phone_number": "9876543210",
                    "created_at": None,
                    "updated_at": None,
                    "is_active": True,
                }
            ],
            25,
        )

        res = self.client.get("/api/v1/tenants?page=2&page_size=10")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["page_size"], 10)
        self.assertEqual(data["total"], 25)
        self.assertEqual(len(data["items"]), 1)

    # 6. Team Members
    @patch("app.repositories.team_repository.TeamRepository.list_team_members")
    def test_team_members_pagination(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_repo.return_value = (
            [
                {
                    "user_id": 10,
                    "name": "Team Alice",
                    "email": "alice@helios.com",
                    "role": "team_member",
                    "phone_number": "1234567890",
                    "staff_id": "TM-10",
                    "designation": "Operator",
                    "is_active": True,
                    "must_change_password": False,
                    "tenant_ids": [1, 2],
                }
            ],
            35,
        )

        res = self.client.get("/api/v1/team-members?page=1&page_size=20")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 20)
        self.assertEqual(data["total"], 35)
        self.assertEqual(len(data["items"]), 1)

    # 7. Support Messages
    @patch("app.repositories.support_repository.SupportRepository.get_messages")
    def test_support_messages_pagination(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_repo.return_value = (
            [
                {
                    "message_id": 1,
                    "tenant_id": 10,
                    "tenant_name": "Client 10",
                    "from_user_id": 3,
                    "from_user_name": "Owner User",
                    "to_user_id": 2,
                    "to_user_name": "Team Member",
                    "message": "Need status update",
                    "message_source": "smb_owner",
                    "status": "open",
                    "created_at": "2024-03-28 10:00:00",
                    "resolved_at": None,
                }
            ],
            48,
        )

        res = self.client.get("/api/v1/support/messages?page=3&page_size=10")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 3)
        self.assertEqual(data["page_size"], 10)
        self.assertEqual(data["total"], 48)
        self.assertEqual(len(data["items"]), 1)

    # 8. Notifications
    @patch("app.repositories.notification_repository.NotificationRepository.list_for_user")
    def test_notifications_pagination(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_repo.return_value = (
            [
                {
                    "notification_id": 1,
                    "tenant_id": 10,
                    "user_id": 3,
                    "message": "Dashboard ready",
                    "type": "dashboard_ready",
                    "is_read": False,
                    "created_at": "2024-03-28 10:00:00",
                }
            ],
            65,
        )

        res = self.client.get("/api/v1/notifications?page=2&page_size=20")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["page_size"], 20)
        self.assertEqual(data["total"], 65)
        self.assertEqual(len(data["items"]), 1)


if __name__ == "__main__":
    unittest.main()

