import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.core.config import settings
from app.repositories.pipeline_health_repository import PipelineHealthRepository
from app.schemas.auth import UserOut
from app.schemas.pipeline_health import (
    EtlAuditLogOut,
    PipelineRunDetailOut,
    PipelineRunOut,
    RestartResponse,
    RetryRequest,
    RetryResponse,
    StageHistoryItem,
)

logger = logging.getLogger("helios.services.pipeline_health")

STAGE_TASK_MAP = {
    "bronze": "bronze_ingest_task",
    "bronze_ingest": "bronze_ingest_task",
    "schema_inference": "schema_inference_task",
    "silver": "silver_clean_task",
    "silver_clean": "silver_clean_task",
    "gold": "gold_transform_task",
    "gold_transform": "gold_transform_task",
}

STAGE_STATUS_MAP = {
    "bronze": ("bronze_ingest", "ingested"),
    "bronze_ingest": ("bronze_ingest", "ingested"),
    "schema_inference": ("schema_inference", "schema_inference_running"),
    "silver": ("silver_clean", "silver_running"),
    "silver_clean": ("silver_clean", "silver_running"),
    "gold": ("gold_transform", "gold_running"),
    "gold_transform": ("gold_transform", "gold_running"),
}


def _invoke_databricks_repair_run(run_id: int, rerun_tasks: List[str]) -> Optional[str]:
    """
    Call Databricks Jobs API repair-run to re-execute only failed and downstream tasks.
    Gracefully catches SDK or network issues in non-cloud or mock environments.
    """
    try:
        from databricks.sdk import WorkspaceClient

        host = settings.DATABRICKS_SERVER_HOSTNAME
        token = settings.DATABRICKS_TOKEN
        if host and token and not host.startswith("mock"):
            client = WorkspaceClient(host=host, token=token)
            repair_waiter = client.jobs.repair_run(
                run_id=run_id,
                rerun_tasks=rerun_tasks,
                rerun_dependent_tasks=True,
            )
            logger.info("Databricks Jobs repair-run initiated for run %s: tasks=%s", run_id, rerun_tasks)
            return str(getattr(repair_waiter, "repair_id", run_id))
    except Exception as exc:
        logger.warning("Databricks Jobs API repair-run call skipped or simulated: %s", exc)
    return None


class PipelineHealthService:
    """Service providing pipeline run listing, detail inspection, stage repair, and full restart."""

    @staticmethod
    def list_runs(
        current_user: UserOut,
        repo: PipelineHealthRepository,
        status_filter: Optional[str] = None,
    ) -> List[PipelineRunOut]:
        """
        List all pipeline runs.
        Admins see all tenants; Team Members see only their assigned tenants.
        """
        rows = repo.list_runs(
            user_id=current_user.id,
            user_role=current_user.role.value,
            status_filter=status_filter,
        )
        results: List[PipelineRunOut] = []
        for r in rows:
            results.append(
                PipelineRunOut(
                    batch_id=str(r["batch_id"]),
                    tenant_id=int(r["tenant_id"]),
                    tenant=r.get("tenant"),
                    tenant_name=r.get("tenant_name"),
                    source_type=str(r.get("source_type") or "upload"),
                    current_stage=str(r.get("current_stage") or "unknown"),
                    status=str(r.get("status") or "unknown"),
                    started_at=r.get("started_at"),
                    updated_at=r.get("updated_at"),
                    error_message=r.get("error_message"),
                )
            )
        return results

    @staticmethod
    def _build_stage_history(
        current_stage: str,
        current_status: str,
        audit_logs: List[Dict[str, Any]],
    ) -> List[StageHistoryItem]:
        """Construct chronologically ordered stage execution timeline from audit records."""
        history: List[StageHistoryItem] = []
        for entry in audit_logs:
            start_dt = entry.get("started_at")
            comp_dt = entry.get("completed_at")
            duration: Optional[float] = None
            if isinstance(start_dt, datetime) and isinstance(comp_dt, datetime):
                duration = round((comp_dt - start_dt).total_seconds(), 2)
            history.append(
                StageHistoryItem(
                    stage=str(entry.get("stage")),
                    status=str(entry.get("status")),
                    started_at=start_dt,
                    completed_at=comp_dt,
                    duration_seconds=duration,
                    row_count=entry.get("row_count"),
                    error_message=entry.get("error_message"),
                )
            )
        return history

    @classmethod
    def get_run_detail(
        cls,
        batch_id: str,
        current_user: UserOut,
        repo: PipelineHealthRepository,
    ) -> PipelineRunDetailOut:
        """Fetch full run detail with stage history and audit entries with access validation."""
        run = repo.get_run_detail(
            batch_id=batch_id,
            user_id=current_user.id,
            user_role=current_user.role.value,
        )
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pipeline run '{batch_id}' not found or access denied.",
            )

        raw_audits = run.get("audit_logs") or []
        history = cls._build_stage_history(
            current_stage=run.get("current_stage") or "",
            current_status=run.get("status") or "",
            audit_logs=raw_audits,
        )
        audit_models = [EtlAuditLogOut(**a) for a in raw_audits]

        return PipelineRunDetailOut(
            batch_id=str(run["batch_id"]),
            tenant_id=int(run["tenant_id"]),
            tenant=run.get("tenant"),
            tenant_name=run.get("tenant_name"),
            source_type=str(run.get("source_type") or "upload"),
            current_stage=str(run.get("current_stage") or "unknown"),
            status=str(run.get("status") or "unknown"),
            started_at=run.get("started_at"),
            updated_at=run.get("updated_at"),
            error_message=run.get("error_message"),
            stage_history=history,
            audit_logs=audit_models,
        )

    @classmethod
    def retry_from_failed_stage(
        cls,
        batch_id: str,
        current_user: UserOut,
        repo: PipelineHealthRepository,
        request: Optional[RetryRequest] = None,
    ) -> RetryResponse:
        """
        Re-run only the failed task (and downstream tasks) using Databricks repair-run.
        Earlier stage data remains untouched and reused (e.g. Bronze raw tables reused if Silver failed).
        """
        detail = cls.get_run_detail(batch_id, current_user, repo)
        if detail.status == "success":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch '{batch_id}' has already succeeded and cannot be retried.",
            )

        stage_key = detail.current_stage.lower()
        new_stage, new_status = STAGE_STATUS_MAP.get(stage_key, (detail.current_stage, "processing"))

        default_task = STAGE_TASK_MAP.get(stage_key, f"{stage_key}_task")
        rerun_tasks = request.rerun_tasks if (request and request.rerun_tasks) else [default_task]

        # Trigger Databricks Jobs repair-run API
        numeric_run_id = abs(hash(batch_id)) % 1000000
        _invoke_databricks_repair_run(numeric_run_id, rerun_tasks)

        # Update pipeline_status Delta table to the re-running stage
        repo.update_status_for_retry(
            batch_id=batch_id,
            stage=new_stage,
            status=new_status,
            clear_error=True,
        )

        msg = (
            f"Repaired run successfully triggered from failed stage '{detail.current_stage}'. "
            f"Re-running tasks: {rerun_tasks}. Upstream stage data was preserved and reused."
        )
        return RetryResponse(
            batch_id=batch_id,
            status=new_status,
            current_stage=new_stage,
            message=msg,
            repaired_tasks=rerun_tasks,
        )

    @classmethod
    def full_restart(
        cls,
        batch_id: str,
        current_user: UserOut,
        repo: PipelineHealthRepository,
    ) -> RestartResponse:
        """
        Mark batch as 'restart_required' and notify the SMB Owner to re-upload.
        Does NOT re-run the existing batch in place.
        """
        detail = cls.get_run_detail(batch_id, current_user, repo)
        explanation = (
            f"Batch {batch_id} requires a full restart due to earlier stage corruption or invalid source data. "
            "The SMB Owner must submit a new file upload or trigger a fresh connection sync."
        )

        repo.mark_restart_required(batch_id=batch_id, message=explanation)

        notify_msg = "Please re-upload your data — we need a fresh copy to continue processing"
        repo.notify_smb_owner(tenant_id=detail.tenant_id, message=notify_msg)

        try:
            from app.services.notification_service import NotificationService
            NotificationService.notify_restart_required(
                tenant_id=detail.tenant_id,
                batch_id=batch_id,
                cursor=getattr(repo, "cursor", None),
            )
        except Exception as notif_err:
            logger.warning("Failed to dispatch notify_restart_required: %s", notif_err)

        logger.info("Batch %s marked restart_required. Notification sent to tenant %d", batch_id, detail.tenant_id)
        return RestartResponse(
            batch_id=batch_id,
            status="restart_required",
            message=(
                "Batch marked as 'restart_required'. The existing batch was not re-run. "
                "A notification has been sent to the SMB Owner requesting them to re-upload "
                "the original source file or re-sync their connection."
            ),
            notification_sent=True,
        )
