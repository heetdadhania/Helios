import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.repositories.confirmation_repository import ConfirmationRepository
from app.schemas.auth import UserOut
from app.schemas.confirmation import (
    CompletenessResponse,
    ConfirmRequest,
    ConfirmResponse,
    PendingUploadOut,
    SchemaPreviewOut,
)

logger = logging.getLogger("helios.services.confirmation")


def trigger_silver_stage(
    batch_id: str,
    tenant_id: int,
    confirmed_template: str,
    column_mapping: Dict[str, Any],
) -> None:
    """
    Hook to trigger Medallion Silver transformation.
    Called immediately upon confirmation to process Bronze data into Silver tables.
    """
    logger.info(
        "Triggering Silver stage for batch %s [tenant=%d, template=%s]",
        batch_id,
        tenant_id,
        confirmed_template,
    )
    from pipeline.runner import submit_batch_run
    submit_batch_run(tenant_id=tenant_id, batch_id=batch_id, start_stage="silver")



import threading

_tenant_confirm_locks: Dict[int, threading.Lock] = {}
_tenant_confirm_locks_guard = threading.Lock()

def _get_tenant_lock(tenant_id: int) -> threading.Lock:
    with _tenant_confirm_locks_guard:
        if tenant_id not in _tenant_confirm_locks:
            _tenant_confirm_locks[tenant_id] = threading.Lock()
        return _tenant_confirm_locks[tenant_id]


class ConfirmationService:
    """Service orchestrating pending schema reviews, previews, human confirmation, and completeness."""

    @staticmethod
    def get_pending_uploads(
        current_user: UserOut,
        repo: ConfirmationRepository,
        tenant_filter: Optional[str] = None,
    ) -> List[PendingUploadOut]:
        """
        Fetch uploads currently in 'awaiting_confirmation' state.
        Admins see all tenants; Team Members see only their assigned tenants.
        """
        raw_pending = repo.get_pending(
            user_id=current_user.id,
            user_role=current_user.role.value,
            tenant_filter=tenant_filter,
        )

        results: List[PendingUploadOut] = []
        for item in raw_pending:
            results.append(
                PendingUploadOut(
                    batch_id=item["batch_id"],
                    tenant_id=int(item["tenant_id"]),
                    tenant_name=item.get("tenant_name"),
                    upload_id=int(item["upload_id"]) if item.get("upload_id") is not None else None,
                    source_type=item.get("source_type") or "upload",
                    filename=item.get("filename") or "upload.data",
                    stage=item.get("stage") or "schema_inference",
                    status=item.get("status") or "pending_review",
                    detected_template=item.get("detected_template"),
                    confidence_score=float(item["confidence_score"]) if item.get("confidence_score") is not None else None,
                    created_at=item.get("created_at"),
                    updated_at=item.get("updated_at"),
                )
            )
        return results

    @staticmethod
    def get_preview(
        batch_id: str,
        current_user: UserOut,
        repo: ConfirmationRepository,
    ) -> SchemaPreviewOut:
        """
        Retrieve schema inference preview with sample rows and internal notes for review.
        Enforces tenant authorization for Team Members.
        """
        meta = repo.get_batch_metadata(batch_id)
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch '{batch_id}' was not found.",
            )

        tenant_id = int(meta["tenant_id"])
        if not repo.check_user_tenant_access(current_user.id, current_user.role.value, tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not assigned to review batches for this organization.",
            )

        preview_data = repo.get_preview(batch_id)
        if not preview_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preview details for batch '{batch_id}' could not be generated.",
            )

        return SchemaPreviewOut(**preview_data)

    @staticmethod
    def confirm_mapping(
        batch_id: str,
        request: ConfirmRequest,
        current_user: UserOut,
        repo: ConfirmationRepository,
    ) -> ConfirmResponse:
        """
        Confirm or correct schema mapping, persist approval and optional internal notes
        to inferred_schema, transition status to 'silver_running', and invoke Silver stage.
        """
        meta = repo.get_batch_metadata(batch_id)
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch '{batch_id}' was not found.",
            )

        tenant_id = int(meta["tenant_id"])
        if not repo.check_user_tenant_access(current_user.id, current_user.role.value, tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to confirm batches for this organization.",
            )

        tenant_lock = _get_tenant_lock(tenant_id)
        with tenant_lock:
            # Re-fetch metadata inside lock to prevent race condition
            current_meta = repo.get_batch_metadata(batch_id) or meta
            current_status = current_meta.get("status")
            if current_status not in ("pending_review", "awaiting_confirmation"):
                if current_status in ("running", "silver_running", "gold_running", "completed"):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Batch '{batch_id}' is already {current_status}.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Batch '{batch_id}' cannot be confirmed because status is '{current_status}'. Must be pending_review.",
                )

            # Block if another batch for the same tenant is currently running (Requirement: 409)
            if repo.is_tenant_running_batch(tenant_id=tenant_id, exclude_batch_id=batch_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Another batch is already actively running for organization {tenant_id}.",
                )

            # Merge corrected mapping over inferred mapping if provided
            inferred_mapping = {}
            raw_mapping = current_meta.get("column_mapping_json")
            if raw_mapping:
                try:
                    inferred_mapping = json.loads(raw_mapping) if isinstance(raw_mapping, str) else raw_mapping
                except Exception:
                    inferred_mapping = {}

            final_mapping = dict(inferred_mapping)
            if request.corrected_mapping:
                final_mapping.update(request.corrected_mapping)

            # Persist confirmation, optional internal notes, and transition status to running
            repo.save_confirmation(
                batch_id=batch_id,
                confirmed_template=request.confirmed_template,
                column_mapping=final_mapping,
                confirmed_by=current_user.id,
                internal_notes=request.internal_notes,
            )

        # Record audit trail entry
        repo.write_audit_trail(
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            action="batch_approved",
            tenant_id=tenant_id,
            batch_id=batch_id,
            reason=request.internal_notes or "Schema approved by reviewer",
            details_json=json.dumps({"confirmed_template": request.confirmed_template, "mapping": final_mapping}),
        )

        # Hand batch to the unified Pipeline Runner via trigger_silver_stage
        trigger_silver_stage(
            batch_id=batch_id,
            tenant_id=tenant_id,
            confirmed_template=request.confirmed_template,
            column_mapping=final_mapping,
        )

        return ConfirmResponse(
            batch_id=batch_id,
            status="silver_running",
            confirmed_template=request.confirmed_template,
            message=f"Batch '{batch_id}' successfully approved with template '{request.confirmed_template}'. Pipeline runner initiated.",
        )


    @classmethod
    def reject_batch(
        cls,
        batch_id: str,
        reason: str,
        current_user: UserOut,
        repo: ConfirmationRepository,
    ) -> Dict[str, Any]:
        """
        Reject an ingestion batch with a mandatory reason (min 5 chars).
        Marks status as rejected, records audit trail, notifies submitter, and leaves Bronze data intact.
        """
        meta = repo.get_batch_metadata(batch_id)
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch '{batch_id}' was not found.",
            )

        tenant_id = int(meta["tenant_id"])
        if not repo.check_user_tenant_access(current_user.id, current_user.role.value, tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to review batches for this organization.",
            )

        cleaned_reason = (reason or "").strip()
        if len(cleaned_reason) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required and must be at least 5 characters.",
            )

        repo.reject_batch(
            batch_id=batch_id,
            reason=cleaned_reason,
            user_id=current_user.id,
            tenant_id=tenant_id,
        )

        # Record audit trail
        repo.write_audit_trail(
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            action="batch_rejected",
            tenant_id=tenant_id,
            batch_id=batch_id,
            reason=cleaned_reason,
        )

        # Notify submitter
        try:
            from app.services.notification_service import NotificationService
            NotificationService.create_notification(
                tenant_id=tenant_id,
                message=f"Your batch {batch_id} was rejected: {cleaned_reason}",
                notification_type="error",
                cursor=repo.cursor,
            )
        except Exception:
            pass

        return {
            "batch_id": batch_id,
            "status": "rejected",
            "message": f"Batch '{batch_id}' has been rejected.",
            "reason": cleaned_reason,
        }

    @staticmethod
    def get_completeness(
        batch_id: str,
        current_user: UserOut,
        repo: ConfirmationRepository,
    ) -> CompletenessResponse:
        """
        Calculate and return data completeness indicator for a batch:
        (rows successfully written to the Silver clean table) / (total rows ingested into Bronze for that batch_id) as a percentage.
        Enforces tenant authorization for Team Members.
        """
        meta = repo.get_batch_metadata(batch_id)
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch '{batch_id}' was not found.",
            )

        tenant_id = int(meta["tenant_id"])
        if not repo.check_user_tenant_access(current_user.id, current_user.role.value, tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to view batches for this organization.",
            )

        metrics = repo.get_completeness_metrics(
            batch_id=batch_id,
            template_name=meta.get("detected_template"),
        )

        return CompletenessResponse(**metrics)
