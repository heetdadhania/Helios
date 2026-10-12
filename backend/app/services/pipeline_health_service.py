import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.core.config import settings
from app.repositories.pipeline_health_repository import PipelineHealthRepository
from app.schemas.auth import UserOut
from app.schemas.pipeline_health import (
    CancelResponse,
    EtlAuditLogOut,
    PipelineRunDetailOut,
    PipelineRunOut,
    RestartResponse,
    RetryRequest,
    RetryResponse,
    StageHistoryItem,
)

logger = logging.getLogger("helios.services.pipeline_health")


class PipelineHealthService:
    """Service providing pipeline run listing, detail inspection, stage repair, cancellation, and full restart."""

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
                    failed_stage=r.get("failed_stage"),
                    failure_message=r.get("failure_message"),
                    failure_next_step=r.get("failure_next_step"),
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
            failed_stage=run.get("failed_stage"),
            failure_message=run.get("failure_message"),
            failure_next_step=run.get("failure_next_step"),
            stage_history=history,
            audit_logs=audit_models,
        )

    @classmethod
    def cancel_run(
        cls,
        batch_id: str,
        current_user: UserOut,
        repo: PipelineHealthRepository,
    ) -> CancelResponse:
        """
        Cancel an actively running pipeline batch.
        """
        detail = cls.get_run_detail(batch_id, current_user, repo)
        status_norm = (detail.status or "").lower()
        if status_norm not in ("running", "ingesting", "silver_running", "gold_running", "processing", "in_progress"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch '{batch_id}' cannot be cancelled because its current status is '{detail.status}'. Only actively running batches may be cancelled.",
            )

        repo.cancel_run(batch_id, current_user.id)
        repo.write_audit_trail(
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            action="batch_cancelled",
            tenant_id=detail.tenant_id,
            batch_id=batch_id,
            reason="Run cancelled by operator",
        )
        logger.info("Batch %s cancelled by user %s (tenant %d)", batch_id, current_user.id, detail.tenant_id)
        return CancelResponse(
            batch_id=batch_id,
            status="cancelled",
            message=f"Pipeline run for batch '{batch_id}' was cancelled.",
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
        Re-run only the failed stage (and downstream stages) using the real pipeline runner.
        Earlier stage data remains untouched and reused (e.g. Bronze raw tables reused if Silver failed).
        """
        from pipeline.runner import submit_batch_run

        detail = cls.get_run_detail(batch_id, current_user, repo)
        if detail.status.lower() in ("success", "completed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch '{batch_id}' has already succeeded and cannot be retried.",
            )

        failed_stage_str = (detail.failed_stage or detail.current_stage or "silver").lower()
        if "gold" in failed_stage_str:
            start_stage = "gold"
        else:
            start_stage = "silver"

        new_stage = f"{start_stage}_running"
        new_status = "running"

        repo.update_status_for_retry(
            batch_id=batch_id,
            stage=new_stage,
            status=new_status,
            clear_error=True,
        )

        repo.write_audit_trail(
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            action="batch_retry",
            tenant_id=detail.tenant_id,
            batch_id=batch_id,
            reason=f"Retry triggered from failed stage '{start_stage}'",
        )

        submit_batch_run(tenant_id=detail.tenant_id, batch_id=batch_id, start_stage=start_stage)

        msg = (
            f"Run successfully triggered from failed stage '{start_stage}'. "
            f"Upstream stage data was preserved and reused."
        )
        return RetryResponse(
            batch_id=batch_id,
            status=new_status,
            current_stage=start_stage,
            message=msg,
            repaired_tasks=[start_stage],
        )

    @classmethod
    def full_restart(
        cls,
        batch_id: str,
        current_user: UserOut,
        repo: PipelineHealthRepository,
    ) -> RestartResponse:
        """
        Mark batch as cancelled and notify the SMB Owner in-app that the data must be sent again.
        Does NOT re-run the existing batch in place.
        """
        detail = cls.get_run_detail(batch_id, current_user, repo)

        explanation = "Needs attention - please resend"
        repo.mark_restart_required(batch_id=batch_id, message=explanation)
        repo.cancel_run(batch_id=batch_id, user_id=current_user.id)

        notify_msg = "Please re-upload your data — we need a fresh copy to continue processing"
        repo.notify_smb_owner(tenant_id=detail.tenant_id, message=notify_msg)

        repo.write_audit_trail(
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            action="batch_full_restart",
            tenant_id=detail.tenant_id,
            batch_id=batch_id,
            reason="Full restart requested: fresh upload required",
        )

        try:
            from app.services.notification_service import NotificationService
            NotificationService.notify_restart_required(
                tenant_id=detail.tenant_id,
                batch_id=batch_id,
                cursor=getattr(repo, "cursor", None),
            )
        except Exception as notif_err:
            logger.warning("Failed to dispatch notify_restart_required: %s", notif_err)

        logger.info("Batch %s marked cancelled/restart_required. Notification sent to tenant %d", batch_id, detail.tenant_id)
        return RestartResponse(
            batch_id=batch_id,
            status="cancelled",
            message=(
                "Batch marked as cancelled. The existing batch was not re-run. "
                "A notification has been sent to the SMB Owner requesting them to re-upload "
                "the original source file or re-sync their connection."
            ),
            notification_sent=True,
        )

