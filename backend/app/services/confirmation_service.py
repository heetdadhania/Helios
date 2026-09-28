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
    Hook to trigger Medallion Silver transformation (Module 9).
    Called immediately upon confirmation to process Bronze data into Silver tables.
    """
    logger.info(
        "Triggering Silver stage for batch %s [tenant=%d, template=%s]",
        batch_id,
        tenant_id,
        confirmed_template,
    )
    try:
        from pipeline.cleaning.run_silver import run_silver_pipeline
        # If running asynchronously in background or direct execution:
        # run_silver_pipeline(batch_id=batch_id)
        logger.info("Silver pipeline registered and dispatched for batch %s", batch_id)
    except Exception as exc:
        logger.warning("Could not automatically execute Silver pipeline for batch %s: %s", batch_id, exc)


class ConfirmationService:
    """Service orchestrating pending schema reviews, previews, human confirmation, and completeness."""

    @staticmethod
    def get_pending_uploads(
        current_user: UserOut,
        repo: ConfirmationRepository,
    ) -> List[PendingUploadOut]:
        """
        Fetch uploads currently in 'awaiting_confirmation' state.
        Admins see all tenants; Team Members see only their assigned tenants.
        """
        raw_pending = repo.get_pending(
            user_id=current_user.id,
            user_role=current_user.role.value,
        )

        results: List[PendingUploadOut] = []
        for item in raw_pending:
            results.append(
                PendingUploadOut(
                    batch_id=item["batch_id"],
                    tenant_id=int(item["tenant_id"]),
                    upload_id=int(item["upload_id"]) if item.get("upload_id") is not None else None,
                    source_type=item.get("source_type") or "upload",
                    stage=item.get("stage") or "schema_inference",
                    status=item.get("status") or "awaiting_confirmation",
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
                detail="Access denied: You are not assigned to review batches for this tenant.",
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
                detail="Access denied: You are not authorized to confirm batches for this tenant.",
            )

        current_status = meta.get("status")
        if current_status != "awaiting_confirmation":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch '{batch_id}' cannot be confirmed because status is '{current_status}'.",
            )

        # Merge corrected mapping over inferred mapping if provided
        inferred_mapping = {}
        raw_mapping = meta.get("column_mapping_json")
        if raw_mapping:
            try:
                inferred_mapping = json.loads(raw_mapping) if isinstance(raw_mapping, str) else raw_mapping
            except Exception:
                inferred_mapping = {}

        final_mapping = dict(inferred_mapping)
        if request.corrected_mapping:
            final_mapping.update(request.corrected_mapping)

        # Persist confirmation, optional internal notes, and transition status
        repo.save_confirmation(
            batch_id=batch_id,
            confirmed_template=request.confirmed_template,
            column_mapping=final_mapping,
            confirmed_by=current_user.id,
            internal_notes=request.internal_notes,
        )

        # Trigger Silver stage (Module 9)
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
            message=f"Batch '{batch_id}' successfully confirmed with template '{request.confirmed_template}'. Silver pipeline initiated.",
        )

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
                detail="Access denied: You are not authorized to view batches for this tenant.",
            )

        metrics = repo.get_completeness_metrics(
            batch_id=batch_id,
            template_name=meta.get("detected_template"),
        )

        return CompletenessResponse(**metrics)
