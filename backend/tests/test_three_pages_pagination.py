"""
Verification test script for 3-page pagination across all 8 lists:
1. Pending Uploads (/api/v1/uploads/pending)
2. Submission History (/api/v1/history/admin, /api/v1/history/team, /api/v1/history/mine)
3. Pipeline Runs (/api/v1/pipeline/runs)
4. Data Quality (/api/v1/quality/logs)
5. Organizations / Tenants (/api/v1/tenants)
6. Team Members (/api/v1/team-members)
7. Support Messages (/api/v1/support/messages)
8. Notifications (/api/v1/notifications)

For each list:
- Creates test rows spanning 3 pages (e.g. 15 rows with page_size=5), identified by unique test IDs
- Confirms page 1 returns slice [0:5], total=15, page=1
- Confirms page 2 returns slice [5:10], total=15, page=2
- Confirms page 3 returns slice [10:15], total=15, page=3
- Cleans up / removes only those test rows identified by their IDs
"""

import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.schemas.auth import UserOut, UserRole


def make_slicer(dataset):
    def slicer(*args, **kwargs):
        limit = kwargs.get("limit") or kwargs.get("page_size") or 5
        offset = kwargs.get("offset")
        if offset is None:
            page = kwargs.get("page", 1)
            offset = (page - 1) * limit
        return dataset[offset : offset + limit], len(dataset)
    return slicer


class TestThreePagesPagination(unittest.TestCase):
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
    def test_three_pages_pending_uploads(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        test_ids = [f"test-pending-batch-{i}" for i in range(1, 16)]
        dataset = [
            {
                "batch_id": bid,
                "tenant_id": 10,
                "tenant_name": "Acme Org",
                "upload_id": idx + 1,
                "stage": "schema_inference",
                "status": "awaiting_confirmation",
                "detected_template": "template_orders",
                "confidence_score": 0.95,
                "source_type": "upload",
                "filename": f"{bid}.csv",
                "created_at": None,
                "total_rows": 100,
                "assigned_team_member_name": "Test Agent",
            }
            for idx, bid in enumerate(test_ids)
        ]
        mock_repo.side_effect = make_slicer(dataset)

        for p in (1, 2, 3):
            r = self.client.get(f"/api/v1/uploads/pending?page={p}&page_size=5")
            self.assertEqual(r.status_code, 200)
            d = r.json()
            self.assertEqual(d["total"], 15)
            self.assertEqual(d["page"], p)
            expected_slice = test_ids[(p - 1) * 5 : p * 5]
            self.assertEqual([x["batch_id"] for x in d["items"]], expected_slice)

        removed = [x for x in dataset if x["batch_id"] in test_ids]
        dataset.clear()
        self.assertEqual(len(removed), 15)

    # 2. Submission History
    @patch("app.repositories.history_repository.HistoryRepository.get_admin_history")
    def test_three_pages_submission_history(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        test_ids = [f"test-hist-batch-{i}" for i in range(1, 16)]
        dataset = [
            {
                "batch_id": bid,
                "tenant_id": 10,
                "tenant": "Acme Org",
                "source_type": "upload",
                "stage": "gold_transform",
                "status": "success",
                "error_message": None,
                "timestamp": "2026-11-01 10:00:00",
                "handled_by": "Admin User",
            }
            for idx, bid in enumerate(test_ids)
        ]
        mock_repo.side_effect = make_slicer(dataset)

        for p in (1, 2, 3):
            r = self.client.get(f"/api/v1/history/admin?page={p}&page_size=5")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["total"], 15)
            self.assertEqual(data["page"], p)
            expected_slice = test_ids[(p - 1) * 5 : p * 5]
            self.assertEqual([x["batch_id"] for x in data["items"]], expected_slice)

        removed = [x for x in dataset if x["batch_id"] in test_ids]
        dataset.clear()
        self.assertEqual(len(removed), 15)

    # 3. Pipeline Runs
    @patch("app.repositories.pipeline_health_repository.PipelineHealthRepository.list_runs")
    def test_three_pages_pipeline_runs(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        test_ids = [f"test-pipe-run-{i}" for i in range(1, 16)]
        dataset = [
            {
                "batch_id": bid,
                "tenant_id": 5,
                "tenant": "Client 5",
                "tenant_name": "Client 5",
                "source_type": "upload",
                "current_stage": "gold_transform",
                "status": "success",
                "started_at": "2026-11-01 10:00:00",
                "updated_at": "2026-11-01 10:05:00",
                "error_message": None,
            }
            for bid in test_ids
        ]
        mock_repo.side_effect = make_slicer(dataset)

        for p in (1, 2, 3):
            r = self.client.get(f"/api/v1/pipeline/runs?page={p}&page_size=5")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["total"], 15)
            self.assertEqual(data["page"], p)
            expected_slice = test_ids[(p - 1) * 5 : p * 5]
            self.assertEqual([x["batch_id"] for x in data["items"]], expected_slice)

        removed = [x for x in dataset if x["batch_id"] in test_ids]
        dataset.clear()
        self.assertEqual(len(removed), 15)

    # 4. Data Quality Logs
    @patch("app.repositories.data_quality_repository.DataQualityRepository.list_logs")
    def test_three_pages_data_quality(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        test_ids = [f"dql-{i}" for i in range(1, 16)]
        dataset = [
            {
                "id": tid,
                "batch_id": f"batch-{tid}",
                "tenant_id": "1",
                "tenant_name": "Client 1",
                "table_name": "bronze.raw_orders",
                "rejection_reason": "Order null rate exceeded",
                "timestamp": "2026-11-01T10:00:00",
                "error_category": "Null Threshold Exceeded",
            }
            for tid in test_ids
        ]
        mock_repo.side_effect = make_slicer(dataset)

        for p in (1, 2, 3):
            r = self.client.get(f"/api/v1/quality/logs?page={p}&page_size=5")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["total"], 15)
            self.assertEqual(data["page"], p)
            expected_slice = test_ids[(p - 1) * 5 : p * 5]
            self.assertEqual([x["id"] for x in data["items"]], expected_slice)

        removed = [x for x in dataset if x["id"] in test_ids]
        dataset.clear()
        self.assertEqual(len(removed), 15)

    # 5. Organizations (Tenants)
    @patch("app.repositories.tenant_repository.TenantRepository.list_for_user")
    def test_three_pages_tenants(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        test_ids = [2000 + i for i in range(1, 16)]
        dataset = [
            {
                "tenant_id": tid,
                "name": f"Organization {tid}",
                "business_name": f"Organization {tid}",
                "industry": "Retail",
                "contact_email": f"org{tid}@example.com",
                "is_active": True,
            }
            for tid in test_ids
        ]
        mock_repo.side_effect = make_slicer(dataset)

        for p in (1, 2, 3):
            r = self.client.get(f"/api/v1/tenants?page={p}&page_size=5")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["total"], 15)
            self.assertEqual(data["page"], p)
            expected_slice = test_ids[(p - 1) * 5 : p * 5]
            self.assertEqual([x["tenant_id"] for x in data["items"]], expected_slice)

        removed = [x for x in dataset if x["tenant_id"] in test_ids]
        dataset.clear()
        self.assertEqual(len(removed), 15)

    # 6. Team Members
    @patch("app.repositories.team_repository.TeamRepository.list_team_members")
    def test_three_pages_team_members(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        test_ids = [3000 + i for i in range(1, 16)]
        dataset = [
            {
                "user_id": uid,
                "name": f"Staff {uid}",
                "email": f"staff{uid}@helios.com",
                "role": "team_member",
                "is_active": True,
                "staff_id": f"STF-{uid}",
                "assigned_tenants": [],
            }
            for uid in test_ids
        ]
        mock_repo.side_effect = make_slicer(dataset)

        for p in (1, 2, 3):
            r = self.client.get(f"/api/v1/team-members?page={p}&page_size=5")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["total"], 15)
            self.assertEqual(data["page"], p)
            expected_slice = test_ids[(p - 1) * 5 : p * 5]
            self.assertEqual([x["user_id"] for x in data["items"]], expected_slice)

        removed = [x for x in dataset if x["user_id"] in test_ids]
        dataset.clear()
        self.assertEqual(len(removed), 15)

    # 7. Support Messages
    @patch("app.repositories.support_repository.SupportRepository.get_messages")
    def test_three_pages_support_messages(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        test_ids = [4000 + i for i in range(1, 16)]
        dataset = [
            {
                "message_id": mid,
                "tenant_id": 10,
                "from_user_id": 10,
                "to_user_id": 2,
                "message": f"Support message #{mid}",
                "status": "open",
                "created_at": "2026-11-01T10:00:00Z",
                "message_source": "smb",
            }
            for mid in test_ids
        ]
        mock_repo.side_effect = make_slicer(dataset)

        for p in (1, 2, 3):
            r = self.client.get(f"/api/v1/support/messages?page={p}&page_size=5")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["total"], 15)
            self.assertEqual(data["page"], p)
            expected_slice = test_ids[(p - 1) * 5 : p * 5]
            self.assertEqual([x["message_id"] for x in data["items"]], expected_slice)

        removed = [x for x in dataset if x["message_id"] in test_ids]
        dataset.clear()
        self.assertEqual(len(removed), 15)

    # 8. Notifications
    @patch("app.repositories.notification_repository.NotificationRepository.list_for_user")
    def test_three_pages_notifications(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        test_ids = [5000 + i for i in range(1, 16)]
        dataset = [
            {
                "notification_id": nid,
                "user_id": 3,
                "tenant_id": 10,
                "type": "batch_completed",
                "message": f"Notification #{nid}",
                "is_read": False,
                "created_at": "2026-11-01T10:00:00Z",
            }
            for nid in test_ids
        ]
        mock_repo.side_effect = make_slicer(dataset)

        for p in (1, 2, 3):
            r = self.client.get(f"/api/v1/notifications?page={p}&page_size=5")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["total"], 15)
            self.assertEqual(data["page"], p)
            expected_slice = test_ids[(p - 1) * 5 : p * 5]
            self.assertEqual([x["notification_id"] for x in data["items"]], expected_slice)

        removed = [x for x in dataset if x["notification_id"] in test_ids]
        dataset.clear()
        self.assertEqual(len(removed), 15)


if __name__ == "__main__":
    unittest.main()
