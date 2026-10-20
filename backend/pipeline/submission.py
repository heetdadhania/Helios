import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.db.base import get_databricks_connection
from pipeline.ingestion.read_source import read_source
from pipeline.ingestion.run_bronze import run_bronze_ingestion
from pipeline.schema_inference.inference_engine import infer_schema_for_batch

logger = logging.getLogger("helios.pipeline.submission")

VOLUME_BASE_PATH = "/Volumes/helios/bronze/uploads"


def _resolve_local_file_path(tenant_id: int, batch_id: str, file_path_or_name: str) -> Path:
    """
    Locates the actual file on local disk or Volume path across OS path variations.
    """
    candidates = [
        Path(file_path_or_name),
        Path(VOLUME_BASE_PATH) / str(tenant_id) / batch_id / Path(file_path_or_name).name,
        Path("storage") / "volumes" / "helios" / "bronze" / "uploads" / str(tenant_id) / batch_id / Path(file_path_or_name).name,
    ]
    
    # Try directory glob if specific filename isn't directly matched
    vol_dir = Path(VOLUME_BASE_PATH) / str(tenant_id) / batch_id
    if vol_dir.exists():
        for child in vol_dir.iterdir():
            if child.is_file():
                candidates.append(child)
                
    fallback_dir = Path("storage") / "volumes" / "helios" / "bronze" / "uploads" / str(tenant_id) / batch_id
    if fallback_dir.exists():
        for child in fallback_dir.iterdir():
            if child.is_file():
                candidates.append(child)

    for p in candidates:
        if p.exists() and p.is_file():
            return p

    raise FileNotFoundError(
        f"Unable to locate source file for tenant {tenant_id}, batch {batch_id}. Checked: {[str(c) for c in candidates]}"
    )


def ingest_and_infer(tenant_id: int, batch_id: str) -> Dict[str, Any]:
    """
    Shared entrypoint orchestrating Bronze Ingestion and Schema Inference.
    Used by File Upload, Database Replication Sync, and API Push.

    1. Sets platform.pipeline_status status='ingesting', stage='bronze_ingest'.
    2. Reads raw data from disk.
    3. Loads raw rows into Bronze (raw_orders or raw_shipping).
    4. Runs Schema Inference (matching against Orders/Shipping templates).
    5. Saves inferred mapping to platform.inferred_schema.
    6. Sets platform.pipeline_status status='pending_review', stage='schema_inference'.
    7. Records audit rows in meta.etl_audit_log.
    8. On failure: sets status='failed', failed_stage, failure_message, failure_next_step.
    """
    catalog = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
    started_at = datetime.now(timezone.utc)
    current_stage = "bronze_ingest"

    logger.info("Starting ingest_and_infer for tenant %d, batch %s", tenant_id, batch_id)

    conn = get_databricks_connection(catalog=catalog)
    cur = conn.cursor()

    try:
        # Step 1: Ensure pipeline status is set to 'ingesting'
        cur.execute(
            f"""
            UPDATE `{catalog}`.`platform`.`pipeline_status`
            SET status = 'ingesting',
                stage = 'bronze_ingest',
                last_heartbeat_at = current_timestamp(),
                started_at = COALESCE(started_at, current_timestamp()),
                updated_at = current_timestamp()
            WHERE batch_id = :batch_id
            """,
            {"batch_id": batch_id},
        )

        # Step 2: Fetch upload details from platform.pending_uploads
        cur.execute(
            f"""
            SELECT upload_id, source_type, file_name, file_path
            FROM `{catalog}`.`platform`.`pending_uploads`
            WHERE tenant_id = :tenant_id AND upload_id = (
                SELECT upload_id FROM `{catalog}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id LIMIT 1
            )
            LIMIT 1
            """,
            {"tenant_id": tenant_id, "batch_id": batch_id},
        )
        upload_row = cur.fetchone()

        if not upload_row:
            # Fallback query directly matching batch_id or most recent upload for tenant
            cur.execute(
                f"""
                SELECT upload_id, source_type, file_name, file_path
                FROM `{catalog}`.`platform`.`pending_uploads`
                WHERE tenant_id = :tenant_id
                ORDER BY uploaded_at DESC
                LIMIT 1
                """,
                {"tenant_id": tenant_id},
            )
            upload_row = cur.fetchone()

        if not upload_row:
            raise RuntimeError(f"No pending_uploads record found for batch {batch_id}")

        upload_id = upload_row[0]
        source_type = upload_row[1] or "upload"
        file_name = upload_row[2] or "upload.data"
        file_path_str = upload_row[3] or file_name

        local_file = _resolve_local_file_path(tenant_id, batch_id, file_path_str)
        logger.info("Resolved file for batch %s: %s", batch_id, local_file)

        records = read_source(local_file)
        if not records:
            raise ValueError(f"Source file {local_file.name} contains 0 data rows.")

        # Step 3: Run Bronze Ingestion
        current_stage = "bronze_ingest"
        bronze_result = run_bronze_ingestion(
            tenant_id=tenant_id,
            batch_id=batch_id,
            source_type=source_type,
            data=records,
            upload_id=upload_id,
            catalog=catalog,
            cursor=cur,
        )

        # Update heartbeat
        cur.execute(
            f"""
            UPDATE `{catalog}`.`platform`.`pipeline_status`
            SET last_heartbeat_at = current_timestamp(),
                updated_at = current_timestamp()
            WHERE batch_id = :batch_id
            """,
            {"batch_id": batch_id},
        )

        # Step 4: Run Schema Inference
        current_stage = "schema_inference"
        inference_result = infer_schema_for_batch(
            batch_id=batch_id,
            tenant_id=tenant_id,
            records=records,
            catalog=catalog,
            cursor=cur,
        )

        # Step 5: Transition pipeline_status to 'pending_review'
        cur.execute(
            f"""
            UPDATE `{catalog}`.`platform`.`pipeline_status`
            SET status = 'pending_review',
                stage = 'schema_inference',
                last_heartbeat_at = current_timestamp(),
                updated_at = current_timestamp()
            WHERE batch_id = :batch_id
            """,
            {"batch_id": batch_id},
        )

        # Ensure pending_uploads status is 'pending'
        cur.execute(
            f"""
            UPDATE `{catalog}`.`platform`.`pending_uploads`
            SET status = 'pending'
            WHERE upload_id = :upload_id
            """,
            {"upload_id": upload_id},
        )

        logger.info("Successfully completed ingest_and_infer for batch %s -> pending_review", batch_id)

        return {
            "status": "pending_review",
            "batch_id": batch_id,
            "tenant_id": tenant_id,
            "bronze": bronze_result,
            "inference": inference_result,
        }

    except Exception as exc:
        err_msg = str(exc)
        logger.exception("ingest_and_infer failed for batch %s at stage %s: %s", batch_id, current_stage, err_msg)
        completed_at = datetime.now(timezone.utc)

        next_step = (
            "Fix the file and send it again"
            if current_stage == "bronze_ingest"
            else "Retry from the failed stage"
        )

        try:
            # Set status to failed with diagnostic details
            cur.execute(
                f"""
                UPDATE `{catalog}`.`platform`.`pipeline_status`
                SET status = 'failed',
                    stage = :stage,
                    failed_stage = :failed_stage,
                    failure_message = :failure_message,
                    failure_next_step = :failure_next_step,
                    error_message = :error_message,
                    last_heartbeat_at = current_timestamp(),
                    updated_at = current_timestamp()
                WHERE batch_id = :batch_id
                """,
                {
                    "batch_id": batch_id,
                    "stage": current_stage,
                    "failed_stage": current_stage,
                    "failure_message": err_msg,
                    "failure_next_step": next_step,
                    "error_message": err_msg,
                },
            )

            # Record failure in meta.etl_audit_log
            cur.execute(
                f"""
                INSERT INTO `{catalog}`.`meta`.`etl_audit_log` (
                    batch_id, stage, row_count, status, started_at, completed_at, error_message
                )
                VALUES (
                    :batch_id, :stage, 0, 'failed', :started_at, :completed_at, :error_message
                )
                """,
                {
                    "batch_id": batch_id,
                    "stage": current_stage,
                    "started_at": started_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "error_message": err_msg,
                },
            )

            # Notify team members and admin of failure
            try:
                from app.services.notification_service import NotificationService
                NotificationService.create_notification(
                    tenant_id=tenant_id,
                    message=f"Ingestion failed for batch {batch_id} during {current_stage}: {err_msg}",
                    notification_type="error",
                    cursor=cur,
                )
            except Exception:
                pass

        except Exception as update_err:
            logger.error("Failed to persist ingestion failure status for batch %s: %s", batch_id, update_err)

        raise exc

    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass
