from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.pipeline_health_repository import PipelineHealthRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.pipeline_health import (
    EtlAuditLogOut,
    PipelineRunDetailOut,
    PipelineRunOut,
    RestartResponse,
    RetryRequest,
    RetryResponse,
    StageHistoryItem,
)
from app.services.pipeline_health_service import PipelineHealthService


class TestPipelineHealthSchemas(unittest.TestCase):
    """Test serialization and validation of pipeline health Pydantic schemas."""

    def test_pipeline_run_out_valid(self):
        run = PipelineRunOut(
            batch_id="batch-001",
            tenant_id=10,
            tenant="Acme Corp",
            source_type="upload",
            current_stage="silver_clean",
            status="silver_running",
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            error_message=None,
        )
        self.assertEqual(run.batch_id, "batch-001")
        self.assertEqual(run.tenant_id, 10)
        self.assertEqual(run.tenant, "Acme Corp")
        self.assertEqual(run.current_stage, "silver_clean")
        self.assertEqual(run.status, "silver_running")

    def test_pipeline_run_detail_out_with_history(self):
        history = [
            StageHistoryItem(
                stage="bronze_ingest",
                status="completed",
                started_at=datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 9, 23, 10, 0, 15, tzinfo=timezone.utc),
                duration_seconds=15.0,
                row_count=500,
            )
        ]
        audit = [
            EtlAuditLogOut(
                log_id=1,
                batch_id="batch-002",
                stage="bronze_ingest",
                row_count=500,
                status="completed",
            )
        ]
        detail = PipelineRunDetailOut(
            batch_id="batch-002",
            tenant_id=20,
            tenant_name="Beta Retail",
            source_type="db_connection",
            current_stage="silver_clean",
            status="failed",
            error_message="Currency parse error",
            stage_history=history,
            audit_logs=audit,
        )
        self.assertEqual(detail.batch_id, "batch-002")
        self.assertEqual(len(detail.stage_history), 1)
        self.assertEqual(detail.stage_history[0].duration_seconds, 15.0)
        self.assertEqual(len(detail.audit_logs), 1)

    def test_retry_and_restart_schemas(self):
        retry_req = RetryRequest(rerun_tasks=["silver_clean_task"], reason="Transient error")
        self.assertEqual(retry_req.rerun_tasks, ["silver_clean_task"])

        retry_res = RetryResponse(
            batch_id="batch-003",
            status="silver_running",
            current_stage="silver_clean",
            message="Repair triggered",
            repaired_tasks=["silver_clean_task"],
        )
        self.assertEqual(retry_res.status, "silver_running")

        restart_res = RestartResponse(
            batch_id="batch-004",
            message="Please re-upload file",
            notification_sent=True,
        )
        self.assertEqual(restart_res.status, "restart_required")
        self.assertTrue(restart_res.notification_sent)


class TestPipelineHealthRepository(unittest.TestCase):
    """Test database queries and constraints in PipelineHealthRepository."""

    def setUp(self):
        self.mock_cursor = MagicMock()
        self.repo = PipelineHealthRepository(self.mock_cursor, catalog="helios")

    def test_check_user_tenant_access_admin(self):
        self.assertTrue(self.repo.check_user_tenant_access(user_id=1, user_role="admin", tenant_id=99))

    def test_check_user_tenant_access_team_member(self):
        self.mock_cursor.fetchone.return_value = (1,)
        self.assertTrue(self.repo.check_user_tenant_access(user_id=2, user_role="team_member", tenant_id=10))

        self.mock_cursor.fetchone.return_value = None
        self.assertFalse(self.repo.check_user_tenant_access(user_id=2, user_role="team_member", tenant_id=20))

    def test_check_user_tenant_access_smb_owner(self):
        self.assertFalse(self.repo.check_user_tenant_access(user_id=3, user_role="smb_owner", tenant_id=10))

    def test_list_runs_admin(self):
        self.mock_cursor.description = [
            ("batch_id",), ("tenant_id",), ("tenant",), ("tenant_name",),
            ("source_type",), ("current_stage",), ("status",), ("started_at",),
            ("updated_at",), ("error_message",),
        ]
        self.mock_cursor.fetchall.return_value = [
            ("b-1", 10, "Acme", "Acme", "upload", "gold_transform", "success", None, None, None)
        ]

        runs = self.repo.list_runs(user_id=1, user_role="admin")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["batch_id"], "b-1")

        calls = self.mock_cursor.execute.call_args_list
        executed_sql = calls[0][0][0]
        self.assertNotIn("team_assignments", executed_sql)

    def test_list_runs_team_member(self):
        self.mock_cursor.description = [
            ("batch_id",), ("tenant_id",), ("tenant",), ("tenant_name",),
            ("source_type",), ("current_stage",), ("status",), ("started_at",),
            ("updated_at",), ("error_message",),
        ]
        self.mock_cursor.fetchall.return_value = [
            ("b-2", 15, "Beta", "Beta", "api_push", "silver_clean", "failed", None, None, "error")
        ]

        runs = self.repo.list_runs(user_id=5, user_role="team_member")
        self.assertEqual(len(runs), 1)

        calls = self.mock_cursor.execute.call_args_list
        executed_sql = calls[0][0][0]
        self.assertIn("team_assignments", executed_sql)

    def test_list_runs_status_filter_running(self):
        self.mock_cursor.description = [
            ("batch_id",), ("tenant_id",), ("tenant",), ("tenant_name",),
            ("source_type",), ("current_stage",), ("status",), ("started_at",),
            ("updated_at",), ("error_message",),
        ]
        self.mock_cursor.fetchall.return_value = []
        self.repo.list_runs(user_id=1, user_role="admin", status_filter="running")
        calls = self.mock_cursor.execute.call_args_list
        executed_sql = calls[0][0][0]
        self.assertIn("LIKE '%running%'", executed_sql)

    def test_list_runs_status_filter_case_insensitive(self):
        self.mock_cursor.description = [
            ("batch_id",), ("tenant_id",), ("tenant",), ("tenant_name",),
            ("source_type",), ("current_stage",), ("status",), ("started_at",),
            ("updated_at",), ("error_message",),
        ]
        self.mock_cursor.fetchall.return_value = []
        self.repo.list_runs(user_id=1, user_role="admin", status_filter="Success")
        calls = self.mock_cursor.execute.call_args_list
        executed_sql = calls[0][0][0]
        self.assertIn("LOWER(ps.status) IN ('success', 'completed')", executed_sql)

    def test_list_runs_status_filter_all(self):
        self.mock_cursor.description = [
            ("batch_id",), ("tenant_id",), ("tenant",), ("tenant_name",),
            ("source_type",), ("current_stage",), ("status",), ("started_at",),
            ("updated_at",), ("error_message",),
        ]
        self.mock_cursor.fetchall.return_value = []
        self.repo.list_runs(user_id=1, user_role="admin", status_filter="all")
        calls = self.mock_cursor.execute.call_args_list
        executed_sql = calls[0][0][0]
        self.assertNotIn("status = 'all'", executed_sql)
        self.assertNotIn("WHERE", executed_sql)

    def test_update_status_for_retry(self):
        self.repo.update_status_for_retry(
            batch_id="b-retry",
            stage="silver_clean",
            status="silver_running",
            clear_error=True,
        )
        calls = self.mock_cursor.execute.call_args_list
        sql, params = calls[0][0]
        self.assertIn("UPDATE", sql)
        self.assertIn("error_message = NULL", sql)
        self.assertEqual(params["batch_id"], "b-retry")
        self.assertEqual(params["stage"], "silver_clean")
        self.assertEqual(params["status"], "silver_running")

    def test_mark_restart_required(self):
        self.mock_cursor.fetchone.return_value = (10, 42)
        self.mock_cursor.description = [("tenant_id",), ("upload_id",)]

        result = self.repo.mark_restart_required("b-restart", "Invalid format")
        self.assertIsNotNone(result)

        calls = self.mock_cursor.execute.call_args_list
        update_ps_sql = calls[1][0][0]
        self.assertIn("restart_required", update_ps_sql)

    def test_notify_smb_owner(self):
        self.mock_cursor.fetchone.return_value = (101,)
        self.mock_cursor.description = [("user_id",)]

        self.repo.notify_smb_owner(tenant_id=10, message="Please re-upload")
        calls = self.mock_cursor.execute.call_args_list
        insert_sql = calls[1][0][0]
        params = calls[1][0][1]
        self.assertIn("notification_log", insert_sql)
        self.assertEqual(params["user_id"], 101)
        self.assertEqual(params["tenant_id"], 10)


class TestPipelineHealthService(unittest.TestCase):
    """Test business logic in PipelineHealthService."""

    def setUp(self):
        self.mock_repo = MagicMock(spec=PipelineHealthRepository)
        self.admin_user = UserOut(
            id=1,
            name="Admin User",
            email="admin@helios.com",
            role=UserRole.ADMIN,
            tenant_id=None,
        )

    def test_retry_from_failed_stage_success(self):
        self.mock_repo.get_run_detail.return_value = {
            "batch_id": "batch-fail",
            "tenant_id": 5,
            "tenant": "Store",
            "source_type": "upload",
            "current_stage": "silver_clean",
            "status": "failed",
            "error_message": "Invalid date format",
            "audit_logs": [],
        }

        with patch("pipeline.runner.submit_batch_run") as mock_runner:
            response = PipelineHealthService.retry_from_failed_stage(
                batch_id="batch-fail",
                current_user=self.admin_user,
                repo=self.mock_repo,
            )

            self.assertEqual(response.batch_id, "batch-fail")
            self.assertEqual(response.status, "running")
            self.assertEqual(response.current_stage, "silver")
            self.assertIn("reused", response.message)

            self.mock_repo.update_status_for_retry.assert_called_once_with(
                batch_id="batch-fail",
                stage="silver_running",
                status="running",
                clear_error=True,
            )
            mock_runner.assert_called_once_with(tenant_id=5, batch_id="batch-fail", start_stage="silver")

    def test_retry_already_successful_raises_400(self):
        self.mock_repo.get_run_detail.return_value = {
            "batch_id": "batch-succ",
            "tenant_id": 5,
            "tenant": "Store",
            "source_type": "upload",
            "current_stage": "gold_transform",
            "status": "success",
            "audit_logs": [],
        }

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            PipelineHealthService.retry_from_failed_stage(
                batch_id="batch-succ",
                current_user=self.admin_user,
                repo=self.mock_repo,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_full_restart_marks_restart_and_notifies(self):
        self.mock_repo.get_run_detail.return_value = {
            "batch_id": "batch-restart",
            "tenant_id": 12,
            "tenant": "Omega",
            "source_type": "upload",
            "current_stage": "bronze_ingest",
            "status": "failed",
            "audit_logs": [],
        }

        response = PipelineHealthService.full_restart(
            batch_id="batch-restart",
            current_user=self.admin_user,
            repo=self.mock_repo,
        )

        self.assertEqual(response.batch_id, "batch-restart")
        self.assertEqual(response.status, "cancelled")
        self.assertTrue(response.notification_sent)

        self.mock_repo.cancel_run.assert_called_once()
        self.mock_repo.notify_smb_owner.assert_called_once()


class TestPipelineHealthAPI(unittest.TestCase):
    """Integration and authorization tests for /api/pipeline endpoints."""

    def setUp(self):
        self.client = TestClient(app)
        self.mock_cursor = MagicMock()
        app.dependency_overrides[get_db_cursor] = lambda: self.mock_cursor

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_smb_owner_forbidden_on_all_pipeline_endpoints(self):
        smb_user = UserOut(
            id=10,
            name="SMB Owner",
            email="owner@store.com",
            role=UserRole.SMB_OWNER,
            tenant_id=1,
        )
        app.dependency_overrides[get_current_user] = lambda: smb_user

        resp_list = self.client.get("/api/pipeline/runs")
        self.assertEqual(resp_list.status_code, 403)

        resp_detail = self.client.get("/api/pipeline/runs/batch-1")
        self.assertEqual(resp_detail.status_code, 403)

        resp_retry = self.client.post("/api/pipeline/runs/batch-1/retry-failed-stage")
        self.assertEqual(resp_retry.status_code, 403)

        resp_restart = self.client.post("/api/pipeline/runs/batch-1/full-restart")
        self.assertEqual(resp_restart.status_code, 403)

    def test_team_member_list_runs_success(self):
        team_user = UserOut(
            id=2,
            name="Team Support",
            email="support@helios.com",
            role=UserRole.TEAM_MEMBER,
            tenant_id=None,
        )
        app.dependency_overrides[get_current_user] = lambda: team_user

        with patch("app.repositories.pipeline_health_repository.PipelineHealthRepository.list_runs") as mock_list:
            mock_list.return_value = [
                {
                    "batch_id": "b-tm-1",
                    "tenant_id": 5,
                    "tenant": "Client 5",
                    "tenant_name": "Client 5",
                    "source_type": "upload",
                    "current_stage": "schema_inference",
                    "status": "awaiting_confirmation",
                    "started_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "error_message": None,
                }
            ]

            response = self.client.get("/api/pipeline/runs")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["batch_id"], "b-tm-1")
            self.assertEqual(data[0]["tenant"], "Client 5")

    def test_admin_get_run_detail_success(self):
        admin_user = UserOut(
            id=1,
            name="Admin User",
            email="admin@helios.com",
            role=UserRole.ADMIN,
            tenant_id=None,
        )
        app.dependency_overrides[get_current_user] = lambda: admin_user

        with patch("app.repositories.pipeline_health_repository.PipelineHealthRepository.get_run_detail") as mock_detail:
            mock_detail.return_value = {
                "batch_id": "b-detail-1",
                "tenant_id": 7,
                "tenant": "Alpha Retail",
                "tenant_name": "Alpha Retail",
                "source_type": "upload",
                "current_stage": "silver_clean",
                "status": "failed",
                "started_at": datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2026, 9, 23, 10, 2, 0, tzinfo=timezone.utc),
                "error_message": "Column mismatch in date",
                "audit_logs": [
                    {
                        "log_id": 101,
                        "batch_id": "b-detail-1",
                        "stage": "bronze_ingest",
                        "row_count": 1000,
                        "status": "completed",
                        "started_at": datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc),
                        "completed_at": datetime(2026, 9, 23, 10, 0, 10, tzinfo=timezone.utc),
                        "error_message": None,
                    }
                ],
            }

            response = self.client.get("/api/pipeline/runs/b-detail-1")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["batch_id"], "b-detail-1")
            self.assertEqual(len(data["stage_history"]), 1)
            self.assertEqual(data["stage_history"][0]["duration_seconds"], 10.0)
            self.assertEqual(len(data["audit_logs"]), 1)

    def test_retry_failed_stage_endpoint(self):
        admin_user = UserOut(
            id=1,
            name="Admin User",
            email="admin@helios.com",
            role=UserRole.ADMIN,
            tenant_id=None,
        )
        app.dependency_overrides[get_current_user] = lambda: admin_user

        with patch.object(PipelineHealthService, "retry_from_failed_stage") as mock_retry:
            mock_retry.return_value = RetryResponse(
                batch_id="b-retry-api",
                status="silver_running",
                current_stage="silver_clean",
                message="Repaired run successfully triggered",
                repaired_tasks=["silver_clean_task"],
            )

            response = self.client.post("/api/pipeline/runs/b-retry-api/retry-failed-stage")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "silver_running")
            self.assertEqual(data["current_stage"], "silver_clean")

    def test_full_restart_endpoint(self):
        admin_user = UserOut(
            id=1,
            name="Admin User",
            email="admin@helios.com",
            role=UserRole.ADMIN,
            tenant_id=None,
        )
        app.dependency_overrides[get_current_user] = lambda: admin_user

        with patch.object(PipelineHealthService, "full_restart") as mock_restart:
            mock_restart.return_value = RestartResponse(
                batch_id="b-restart-api",
                status="restart_required",
                message="Batch marked as 'restart_required'. A notification has been sent to SMB Owner.",
                notification_sent=True,
            )

            response = self.client.post("/api/pipeline/runs/b-restart-api/full-restart")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "restart_required")
            self.assertTrue(data["notification_sent"])
            self.assertIn("notification", data["message"])
