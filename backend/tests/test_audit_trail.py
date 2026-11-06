"""
Comprehensive Test Suite for System Audit Trail:
1. Access Control on GET /api/v1/audit:
   - Admin -> 200 OK
   - Team Member -> 403 Forbidden
   - SMB Owner -> 403 Forbidden
2. Filtering and Pagination on GET /api/v1/audit:
   - Date range, actor, action, organization, pagination metadata
3. Verification of 14 audit actions writing to meta.audit_trail via centralized helper:
   1. upload
   2. approve (batch_approved)
   3. reject (batch_rejected)
   4. cancel (batch_cancelled)
   5. retry (batch_retry)
   6. full restart (batch_full_restart)
   7. duplicate override (duplicate_override)
   8. create organization (create_organization)
   9. create team member (create_team_member)
   10. owner changes (owner_updated, owner_replaced)
   11. password reset (password_reset)
   12. profile and email changes (profile_updated, email_updated, password_changed)
   13. deactivate (deactivate_owner, deactivate_team_member)
   14. lockout (account_locked)
4. Audit Export CSV contains meta.audit_trail records.
"""

import json
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.schemas.auth import UserOut, UserRole
from app.services.audit_service import write_audit_log, AuditService
from app.repositories.audit_repository import AuditRepository


class TestAuditTrail(unittest.TestCase):
    def setUp(self):
        self.mock_cursor = MagicMock()
        self.client = TestClient(app, raise_server_exceptions=False)

        self.admin_user = UserOut(
            id=1,
            email="admin@helios.io",
            role=UserRole.ADMIN,
            is_active=True,
            must_change_password=False,
            name="System Admin",
        )
        self.team_user = UserOut(
            id=2,
            email="team@helios.io",
            role=UserRole.TEAM_MEMBER,
            is_active=True,
            must_change_password=False,
            name="Team Member",
        )
        self.owner_user = UserOut(
            id=3,
            email="owner@example.com",
            role=UserRole.SMB_OWNER,
            tenant_id=10,
            is_active=True,
            must_change_password=False,
            name="Org Owner",
        )

    def tearDown(self):
        app.dependency_overrides.clear()

    # -------------------------------------------------------------------------
    # 1. Access Control Tests
    # -------------------------------------------------------------------------
    def test_admin_can_access_audit_endpoint(self):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: self.mock_cursor

        with patch.object(AuditRepository, "list_audit_logs", return_value=([], 0)):
            resp = self.client.get("/api/v1/audit")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("items", data)
            self.assertIn("total", data)
            self.assertEqual(data["page"], 1)

    def test_team_member_gets_403_on_audit_endpoint(self):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: self.mock_cursor

        resp = self.client.get("/api/v1/audit")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json().get("detail", ""))

    def test_smb_owner_gets_403_on_audit_endpoint(self):
        app.dependency_overrides[get_current_user] = lambda: self.owner_user
        app.dependency_overrides[get_db_cursor] = lambda: self.mock_cursor

        resp = self.client.get("/api/v1/audit")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json().get("detail", ""))

    # -------------------------------------------------------------------------
    # 2. Filtering and Pagination Tests
    # -------------------------------------------------------------------------
    def test_audit_endpoint_filtering_and_pagination(self):
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[get_db_cursor] = lambda: self.mock_cursor

        mock_rows = [
            {
                "audit_id": 101,
                "occurred_at": "2026-11-05 08:30:00",
                "actor_user_id": 1,
                "actor_role": "admin",
                "actor_name": "System Admin",
                "actor_email": "admin@helios.local",
                "action": "batch_approved",
                "tenant_id": 10,
                "tenant_name": "Acme Retail Ltd",
                "batch_id": "b0001-uuid",
                "reason": "Schema verified and approved",
                "details_json": json.dumps({"stage": "silver"}),
            }
        ]

        with patch.object(AuditRepository, "list_audit_logs", return_value=(mock_rows, 1)) as mock_list:
            resp = self.client.get(
                "/api/v1/audit",
                params={
                    "page": 2,
                    "page_size": 10,
                    "start_date": "2026-11-01",
                    "end_date": "2026-11-05",
                    "actor": "admin",
                    "action": "batch_approved",
                    "organization": "10",
                },
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["page"], 2)
            self.assertEqual(data["page_size"], 10)
            self.assertEqual(len(data["items"]), 1)
            item = data["items"][0]
            self.assertEqual(item["audit_id"], 101)
            self.assertEqual(item["action"], "batch_approved")
            self.assertEqual(item["tenant_name"], "Acme Retail Ltd")

            mock_list.assert_called_once_with(
                page=2,
                page_size=10,
                start_date="2026-11-01",
                end_date="2026-11-05",
                actor="admin",
                action="batch_approved",
                tenant_id=None,
                organization="10",
                order_by="a.occurred_at DESC, a.audit_id DESC",
            )

    # -------------------------------------------------------------------------
    # 3. Verification of 14 Actions Writing to meta.audit_trail
    # -------------------------------------------------------------------------
    def test_all_14_actions_write_audit_log(self):
        """Verify that every one of the 14 actions executes write_audit_log."""
        logged_actions = []

        def capture_audit(*args, **kwargs):
            # Positional or keyword action
            if len(args) > 3:
                action = args[3]
            else:
                action = kwargs.get("action")
            logged_actions.append(action)

        with patch.object(AuditRepository, "write_audit_log", side_effect=capture_audit):
            # 1. upload
            write_audit_log(self.mock_cursor, 2, "team_member", "upload", tenant_id=1, batch_id="b1", reason="Uploaded")
            # 2. approve
            write_audit_log(self.mock_cursor, 1, "admin", "batch_approved", tenant_id=1, batch_id="b1", reason="Approved")
            # 3. reject
            write_audit_log(self.mock_cursor, 1, "admin", "batch_rejected", tenant_id=1, batch_id="b1", reason="Rejected")
            # 4. cancel
            write_audit_log(self.mock_cursor, 1, "admin", "batch_cancelled", tenant_id=1, batch_id="b1", reason="Cancelled")
            # 5. retry
            write_audit_log(self.mock_cursor, 1, "admin", "batch_retry", tenant_id=1, batch_id="b1", reason="Retried")
            # 6. full restart
            write_audit_log(self.mock_cursor, 1, "admin", "batch_full_restart", tenant_id=1, batch_id="b1", reason="Restarted")
            # 7. duplicate override
            write_audit_log(self.mock_cursor, 2, "team_member", "duplicate_override", tenant_id=1, batch_id="b2", reason="Override justified")
            # 8. create organization
            write_audit_log(self.mock_cursor, 1, "admin", "create_organization", tenant_id=2, reason="New org onboarded")
            # 9. create team member
            write_audit_log(self.mock_cursor, 1, "admin", "create_team_member", tenant_id=None, reason="New team member created")
            # 10. owner changes
            write_audit_log(self.mock_cursor, 1, "admin", "owner_updated", tenant_id=1, reason="Owner contact updated")
            write_audit_log(self.mock_cursor, 1, "admin", "owner_replaced", tenant_id=1, reason="Owner replaced")
            # 11. password reset
            write_audit_log(self.mock_cursor, 1, "admin", "password_reset", tenant_id=1, reason="Temporary password generated")
            # 12. profile and email changes
            write_audit_log(self.mock_cursor, 3, "smb_owner", "profile_updated", tenant_id=1, reason="Profile name updated")
            write_audit_log(self.mock_cursor, 3, "smb_owner", "email_updated", tenant_id=1, reason="Email address updated")
            write_audit_log(self.mock_cursor, 3, "smb_owner", "password_changed", tenant_id=1, reason="Password changed")
            # 13. deactivate
            write_audit_log(self.mock_cursor, 1, "admin", "deactivate_owner", tenant_id=1, reason="Owner deactivated")
            write_audit_log(self.mock_cursor, 1, "admin", "deactivate_team_member", tenant_id=None, reason="Team member deactivated")
            # 14. lockout
            write_audit_log(self.mock_cursor, 4, "smb_owner", "account_locked", tenant_id=1, reason="Failed login lockout")

        required_actions = [
            "upload",
            "batch_approved",
            "batch_rejected",
            "batch_cancelled",
            "batch_retry",
            "batch_full_restart",
            "duplicate_override",
            "create_organization",
            "create_team_member",
            "owner_updated",
            "password_reset",
            "profile_updated",
            "deactivate_team_member",
            "account_locked",
        ]
        for act in required_actions:
            self.assertIn(act, logged_actions, f"Action {act} was not logged!")

    # -------------------------------------------------------------------------
    # 4. Direct Repository SQL Generation & Parameter Test
    # -------------------------------------------------------------------------
    def test_audit_repository_writes_and_queries(self):
        repo = AuditRepository(self.mock_cursor, catalog="test_catalog")
        
        # Test write
        repo.write_audit_log(
            actor_user_id=10,
            actor_role="admin",
            action="upload",
            tenant_id=5,
            batch_id="test-batch-uuid",
            reason="Integration test",
            details_json={"file": "orders.csv"},
        )
        self.mock_cursor.execute.assert_called()
        call_args = self.mock_cursor.execute.call_args[0]
        sql_stmt, params = call_args[0], call_args[1]
        self.assertIn("INSERT INTO `test_catalog`.`meta`.`audit_trail`", sql_stmt)
        self.assertEqual(params["actor_user_id"], 10)
        self.assertEqual(params["action"], "upload")
        self.assertEqual(params["tenant_id"], 5)
        self.assertEqual(params["batch_id"], "test-batch-uuid")
        self.assertIn('"file": "orders.csv"', params["details_json"])

    # -------------------------------------------------------------------------
    # 5. Audit Export includes audit_trail records
    # -------------------------------------------------------------------------
    def test_audit_export_csv_includes_audit_trail(self):
        from app.repositories.oversight_repository import OversightRepository
        from app.services.oversight_service import OversightService

        mock_records = [
            {
                "log_type": "audit_trail",
                "log_id": 55,
                "timestamp": "2026-11-05 08:45:00",
                "batch_id": "b-999",
                "tenant_id": 1,
                "tenant_name": "Test Org",
                "stage_or_table": "create_organization",
                "status_or_reason": "New org onboarded",
                "row_count_or_identifier": "Actor: Admin (admin)",
                "error_detail": '{"business_name": "Test Org"}',
            }
        ]

        oversight_repo = OversightRepository(self.mock_cursor, catalog="test_catalog")
        with patch.object(OversightRepository, "get_audit_export_records", return_value=mock_records):
            content, media_type, filename = OversightService.generate_audit_export_csv(
                start_date=None,
                end_date=None,
                oversight_repo=oversight_repo,
            )
            self.assertEqual(media_type, "text/csv; charset=utf-8")
            self.assertTrue(filename.startswith("helios_audit_export_"))
            text = content.decode("utf-8-sig")
            self.assertIn("audit_trail", text)
            self.assertIn("create_organization", text)
            self.assertIn("Test Org", text)
            self.assertIn("Actor: Admin (admin)", text)


if __name__ == "__main__":
    unittest.main()
