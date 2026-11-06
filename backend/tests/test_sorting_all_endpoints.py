"""
Unit tests validating server-side sorting across all 8 endpoints:
1. Organizations (/api/v1/tenants)
2. Team Members (/api/v1/team-members)
3. Pending Uploads (/api/v1/uploads/pending)
4. Submission History (/api/v1/history/admin, /api/v1/history/team, /api/v1/history/mine)
5. Pipeline Health (/api/v1/pipeline/runs)
6. Data Quality (/api/v1/quality/logs)
7. Support Messages (/api/v1/support/messages)
8. Audit Trail (/api/v1/audit)

Verifies:
- Invalid sort_by triggers HTTP 422 Unprocessable Entity
- Invalid sort_order triggers HTTP 422 Unprocessable Entity
- All allowed sort fields resolve safely to non-injected SQL clauses
- Default sort order applies when sort_by is omitted
"""

import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.schemas.auth import UserOut, UserRole


class TestSortingAllEndpoints(unittest.TestCase):
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

    # 1. Organizations (/api/v1/tenants)
    @patch("app.repositories.tenant_repository.TenantRepository.list_for_user")
    def test_organizations_sorting(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        mock_repo.return_value = ([], 0)

        # 422 on invalid sort_by
        res_bad = self.client.get("/api/v1/tenants?sort_by=hacked_column")
        self.assertEqual(res_bad.status_code, 422)

        # 422 on invalid sort_order
        res_bad_order = self.client.get("/api/v1/tenants?sort_by=name&sort_order=diagonal")
        self.assertEqual(res_bad_order.status_code, 422)

        # Allowed fields: id, name, industry, state, created, last data, status
        allowed = ["id", "name", "industry", "state", "created", "last data", "last_data", "status"]
        for field in allowed:
            res_asc = self.client.get(f"/api/v1/tenants?sort_by={field}&sort_order=asc")
            self.assertEqual(res_asc.status_code, 200)
            self.assertIn("ASC", mock_repo.call_args[1]["order_by"])

            res_desc = self.client.get(f"/api/v1/tenants?sort_by={field}&sort_order=desc")
            self.assertEqual(res_desc.status_code, 200)
            self.assertIn("DESC", mock_repo.call_args[1]["order_by"])

        # Default order
        res_def = self.client.get("/api/v1/tenants")
        self.assertEqual(res_def.status_code, 200)
        self.assertEqual(mock_repo.call_args[1]["order_by"], "t.tenant_id ASC")

    # 2. Team Members (/api/v1/team-members)
    @patch("app.repositories.team_repository.TeamRepository.list_team_members")
    def test_team_members_sorting(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        mock_repo.return_value = ([], 0)

        # 422 on invalid sort_by
        res_bad = self.client.get("/api/v1/team-members?sort_by=bogus_field")
        self.assertEqual(res_bad.status_code, 422)

        # Allowed fields: id, name, email, designation, assigned count, created, status
        allowed = ["id", "name", "email", "designation", "assigned count", "assigned_count", "created", "status"]
        for field in allowed:
            res = self.client.get(f"/api/v1/team-members?sort_by={field}&sort_order=desc")
            self.assertEqual(res.status_code, 200)
            self.assertIn("DESC", mock_repo.call_args[1]["order_by"])

        res_def = self.client.get("/api/v1/team-members")
        self.assertEqual(res_def.status_code, 200)
        self.assertEqual(mock_repo.call_args[1]["order_by"], "u.user_id ASC")

    # 3. Pending Uploads (/api/v1/uploads/pending)
    @patch("app.repositories.confirmation_repository.ConfirmationRepository.get_pending")
    def test_pending_uploads_sorting(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        mock_repo.return_value = ([], 0)

        res_bad = self.client.get("/api/v1/uploads/pending?sort_by=not_allowed")
        self.assertEqual(res_bad.status_code, 422)

        # Allowed fields: date, organization, source, status
        allowed = ["date", "organization", "source", "status"]
        for field in allowed:
            res = self.client.get(f"/api/v1/uploads/pending?sort_by={field}&sort_order=asc")
            self.assertEqual(res.status_code, 200)
            self.assertIn("ASC", mock_repo.call_args[1]["order_by"])

        res_def = self.client.get("/api/v1/uploads/pending")
        self.assertEqual(res_def.status_code, 200)
        self.assertEqual(mock_repo.call_args[1]["order_by"], "ps.created_at DESC")

    # 4. Submission History (/api/v1/history/admin, /api/v1/history/team, /api/v1/history/mine)
    @patch("app.repositories.history_repository.HistoryRepository.get_admin_history")
    def test_admin_history_sorting(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        mock_repo.return_value = ([], 0)

        res_bad = self.client.get("/api/v1/history/admin?sort_by=bad_col")
        self.assertEqual(res_bad.status_code, 422)

        # Allowed: date, organization, source, status
        for field in ["date", "organization", "source", "status"]:
            res = self.client.get(f"/api/v1/history/admin?sort_by={field}&sort_order=desc")
            self.assertEqual(res.status_code, 200)
            self.assertIn("DESC", mock_repo.call_args[1]["order_by"])

        res_def = self.client.get("/api/v1/history/admin")
        self.assertEqual(res_def.status_code, 200)
        self.assertEqual(mock_repo.call_args[1]["order_by"], "ps.created_at DESC")

    @patch("app.repositories.history_repository.HistoryRepository.get_team_history")
    def test_team_history_sorting(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        mock_repo.return_value = ([], 0)

        res_bad = self.client.get("/api/v1/history/team?sort_by=invalid")
        self.assertEqual(res_bad.status_code, 422)

        res = self.client.get("/api/v1/history/team?sort_by=status&sort_order=asc")
        self.assertEqual(res.status_code, 200)
        self.assertIn("ASC", mock_repo.call_args[1]["order_by"])

    @patch("app.repositories.history_repository.HistoryRepository.get_smb_history")
    def test_smb_history_sorting(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        mock_repo.return_value = ([], 0)

        res_bad = self.client.get("/api/v1/history/mine?sort_by=unknown")
        self.assertEqual(res_bad.status_code, 422)

        res = self.client.get("/api/v1/history/mine?sort_by=date&sort_order=desc")
        self.assertEqual(res.status_code, 200)
        self.assertIn("DESC", mock_repo.call_args[1]["order_by"])

    # 5. Pipeline Health (/api/v1/pipeline/runs)
    @patch("app.repositories.pipeline_health_repository.PipelineHealthRepository.list_runs")
    def test_pipeline_runs_sorting(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        mock_repo.return_value = ([], 0)

        res_bad = self.client.get("/api/v1/pipeline/runs?sort_by=foo")
        self.assertEqual(res_bad.status_code, 422)

        # Allowed fields: updated, organization, stage, status
        for field in ["updated", "organization", "stage", "status"]:
            res = self.client.get(f"/api/v1/pipeline/runs?sort_by={field}&sort_order=asc")
            self.assertEqual(res.status_code, 200)
            self.assertIn("ASC", mock_repo.call_args[1]["order_by"])

        res_def = self.client.get("/api/v1/pipeline/runs")
        self.assertEqual(res_def.status_code, 200)
        self.assertEqual(mock_repo.call_args[1]["order_by"], "ps.created_at DESC")

    # 6. Data Quality (/api/v1/quality/logs)
    @patch("app.repositories.data_quality_repository.DataQualityRepository.list_logs")
    def test_data_quality_sorting(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        mock_repo.return_value = ([], 0)

        res_bad = self.client.get("/api/v1/quality/logs?sort_by=drop_table")
        self.assertEqual(res_bad.status_code, 422)

        # Allowed fields: time, organization, table, reason
        for field in ["time", "organization", "table", "reason"]:
            res = self.client.get(f"/api/v1/quality/logs?sort_by={field}&sort_order=desc")
            self.assertEqual(res.status_code, 200)
            self.assertIn("DESC", mock_repo.call_args[1]["order_by"])

        res_def = self.client.get("/api/v1/quality/logs")
        self.assertEqual(res_def.status_code, 200)
        self.assertEqual(mock_repo.call_args[1]["order_by"], "d.logged_at DESC")

    # 7. Support Inbox (/api/v1/support/messages)
    @patch("app.repositories.support_repository.SupportRepository.get_messages")
    def test_support_messages_sorting(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        mock_repo.return_value = ([], 0)

        res_bad = self.client.get("/api/v1/support/messages?sort_by=secret")
        self.assertEqual(res_bad.status_code, 422)

        # Allowed fields: date, organization, status, source
        for field in ["date", "organization", "status", "source"]:
            res = self.client.get(f"/api/v1/support/messages?sort_by={field}&sort_order=asc")
            self.assertEqual(res.status_code, 200)
            self.assertIn("ASC", mock_repo.call_args[1]["order_by"])

        res_def = self.client.get("/api/v1/support/messages")
        self.assertEqual(res_def.status_code, 200)
        self.assertEqual(mock_repo.call_args[1]["order_by"], "sm.created_at DESC")

    # 8. Audit Trail (/api/v1/audit)
    @patch("app.repositories.audit_repository.AuditRepository.list_audit_logs")
    def test_audit_trail_sorting(self, mock_repo):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        mock_repo.return_value = ([], 0)

        res_bad = self.client.get("/api/v1/audit?sort_by=fake_col")
        self.assertEqual(res_bad.status_code, 422)

        # Allowed fields: time, actor, action, organization
        for field in ["time", "actor", "action", "organization"]:
            res = self.client.get(f"/api/v1/audit?sort_by={field}&sort_order=desc")
            self.assertEqual(res.status_code, 200)
            self.assertIn("DESC", mock_repo.call_args[1]["order_by"])

        res_def = self.client.get("/api/v1/audit")
        self.assertEqual(res_def.status_code, 200)
        self.assertEqual(mock_repo.call_args[1]["order_by"], "a.occurred_at DESC, a.audit_id DESC")


if __name__ == "__main__":
    unittest.main()

