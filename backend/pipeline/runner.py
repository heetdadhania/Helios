import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings
from app.db.base import get_databricks_connection
from pipeline.cleaning.run_silver import run_silver_pipeline

logger = logging.getLogger("helios.pipeline.runner")

# Background executor owned by backend (2 workers)
pipeline_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="helios-pipeline")


def _is_cancel_requested(cursor, catalog: str, batch_id: str) -> bool:
    """Check if cancellation has been requested for this batch."""
    query = f"""
        SELECT cancel_requested 
        FROM `{catalog}`.`platform`.`pipeline_status` 
        WHERE batch_id = :batch_id 
        LIMIT 1
    """
    cursor.execute(query, {"batch_id": batch_id})
    row = cursor.fetchone()
    return bool(row and row[0])


def _mark_as_cancelled(cursor, catalog: str, batch_id: str, tenant_id: int) -> None:
    """Transition batch to cleanly cancelled state and record audit trail."""
    cursor.execute(
        f"""
        UPDATE `{catalog}`.`platform`.`pipeline_status`
        SET status = 'cancelled',
            stage = 'cancelled',
            updated_at = current_timestamp()
        WHERE batch_id = :batch_id
        """,
        {"batch_id": batch_id},
    )

    try:
        cursor.execute(
            f"""
            INSERT INTO `{catalog}`.`meta`.`audit_trail` (
                occurred_at, actor_user_id, actor_role, action, tenant_id, batch_id, reason, details_json
            )
            VALUES (
                current_timestamp(), NULL, 'system', 'batch_cancelled', :tenant_id, :batch_id, 'Run stopped per cancel request', NULL
            )
            """,
            {"tenant_id": tenant_id, "batch_id": batch_id},
        )
    except Exception as e:
        logger.warning("Failed to write audit trail for cancel: %s", e)


def run_batch(tenant_id: int, batch_id: str, start_stage: str = "silver") -> Dict[str, Any]:
    """
    Unified Pipeline Runner executing Silver and Gold stages sequentially.
    """
    catalog = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
    started_at = datetime.now(timezone.utc)
    current_stage = start_stage

    logger.info("run_batch started for tenant %d, batch %s from stage %s", tenant_id, batch_id, start_stage)

    conn = get_databricks_connection(catalog=catalog)
    cur = conn.cursor()

    try:
        # Check cancellation before starting
        if _is_cancel_requested(cur, catalog, batch_id):
            logger.info("Batch %s was cancelled before execution.", batch_id)
            _mark_as_cancelled(cur, catalog, batch_id, tenant_id)
            return {"batch_id": batch_id, "status": "cancelled"}

        # -------------------------------------------------------------
        # STAGE 1: SILVER CLEANING & STANDARDIZATION
        # -------------------------------------------------------------
        if start_stage.lower() in ("silver", "silver_clean", "silver_running"):
            current_stage = "silver_clean"

            cur.execute(
                f"""
                UPDATE `{catalog}`.`platform`.`pipeline_status`
                SET status = 'silver_running',
                    stage = 'silver_running',
                    last_heartbeat_at = current_timestamp(),
                    updated_at = current_timestamp()
                WHERE batch_id = :batch_id
                """,
                {"batch_id": batch_id},
            )

            # Call real Silver pipeline logic
            silver_result = run_silver_pipeline(
                batch_id=batch_id,
                catalog=catalog,
                cursor=cur,
            )

            # Check cancellation post-silver
            if _is_cancel_requested(cur, catalog, batch_id):
                logger.info("Batch %s cancelled after Silver stage.", batch_id)
                _mark_as_cancelled(cur, catalog, batch_id, tenant_id)
                return {"batch_id": batch_id, "status": "cancelled"}

        # -------------------------------------------------------------
        # STAGE 2: GOLD STORED PROCEDURE & LAKEHOUSE ROLLUPS
        # -------------------------------------------------------------
        current_stage = "gold_transform"

        cur.execute(
            f"""
            UPDATE `{catalog}`.`platform`.`pipeline_status`
            SET status = 'gold_running',
                stage = 'gold_running',
                last_heartbeat_at = current_timestamp(),
                updated_at = current_timestamp()
            WHERE batch_id = :batch_id
            """,
            {"batch_id": batch_id},
        )

        gold_start = datetime.now(timezone.utc)

        # Call the real Gold orchestration procedure
        cur.execute(f"CALL `{catalog}`.`gold`.`sp_run_gold_pipeline`({tenant_id}, '{batch_id}')")

        # Check cancellation post-gold
        if _is_cancel_requested(cur, catalog, batch_id):
            logger.info("Batch %s cancelled after Gold procedure.", batch_id)
            _mark_as_cancelled(cur, catalog, batch_id, tenant_id)
            return {"batch_id": batch_id, "status": "cancelled"}

        # -------------------------------------------------------------
        # STAGE 3: SUCCESS & NOTIFICATIONS
        # -------------------------------------------------------------
        cur.execute(
            f"""
            UPDATE `{catalog}`.`platform`.`pipeline_status`
            SET status = 'success',
                stage = 'gold_transform',
                finished_at = current_timestamp(),
                last_heartbeat_at = current_timestamp(),
                error_message = NULL,
                updated_at = current_timestamp()
            WHERE batch_id = :batch_id
            """,
            {"batch_id": batch_id},
        )

        # Write audit trail row
        try:
            from app.services.oversight_service import OversightService
            OversightService.clear_cache()
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                INSERT INTO `{catalog}`.`meta`.`audit_trail` (
                    occurred_at, actor_user_id, actor_role, action, tenant_id, batch_id, reason, details_json
                )
                VALUES (
                    current_timestamp(), NULL, 'system', 'batch_completed', :tenant_id, :batch_id, 'Pipeline finished successfully', NULL
                )
                """,
                {"tenant_id": tenant_id, "batch_id": batch_id},
            )
        except Exception as audit_err:
            logger.warning("Failed to record completion audit: %s", audit_err)

        # Notify the SMB Owner of this tenant: "Your dashboard is ready"
        try:
            cur.execute(
                f"""
                SELECT user_id FROM `{catalog}`.`platform`.`users`
                WHERE tenant_id = :tenant_id AND role = 'smb_owner' AND is_active = true
                LIMIT 1
                """,
                {"tenant_id": tenant_id},
            )
            smb_user = cur.fetchone()
            owner_id = smb_user[0] if smb_user else None

            cur.execute(
                f"""
                INSERT INTO `{catalog}`.`platform`.`notification_log` (
                    tenant_id, user_id, message, type, is_read, created_at
                )
                VALUES (
                    :tenant_id, :user_id, 'Your dashboard is ready', 'pipeline_success', false, current_timestamp()
                )
                """,
                {"tenant_id": tenant_id, "user_id": owner_id},
            )
        except Exception as notif_err:
            logger.warning("Failed to dispatch completion notification: %s", notif_err)

        logger.info("Pipeline batch %s finished with SUCCESS for tenant %d", batch_id, tenant_id)
        return {"batch_id": batch_id, "status": "success"}

    except Exception as exc:
        err_msg = str(exc)
        logger.exception("Pipeline run_batch failed for batch %s at stage %s: %s", batch_id, current_stage, err_msg)
        completed_at = datetime.now(timezone.utc)

        failure_next_step = "Retry from the failed stage"

        try:
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
                    "failure_next_step": failure_next_step,
                    "error_message": err_msg,
                },
            )

            # Record in meta.etl_audit_log
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

            # Alert assigned Team Member and Admin
            try:
                cur.execute(
                    f"""
                    INSERT INTO `{catalog}`.`platform`.`notification_log` (
                        tenant_id, user_id, message, type, is_read, created_at
                    )
                    VALUES (
                        :tenant_id, NULL, :msg, 'error', false, current_timestamp()
                    )
                    """,
                    {
                        "tenant_id": tenant_id,
                        "msg": f"Pipeline failure on batch {batch_id} ({current_stage}): {err_msg}",
                    },
                )
            except Exception:
                pass

        except Exception as update_err:
            logger.error("Failed to persist run failure for batch %s: %s", batch_id, update_err)

        try:
            from app.services.oversight_service import OversightService
            OversightService.clear_cache()
        except Exception:
            pass

        raise exc

    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


def submit_batch_run(tenant_id: int, batch_id: str, start_stage: str = "silver") -> None:
    """Submit batch to the background executor."""
    pipeline_executor.submit(run_batch, tenant_id, batch_id, start_stage)
    logger.info("Submitted batch %s for background processing (stage=%s)", batch_id, start_stage)


def mark_stalled_runs_on_startup() -> int:
    """
    On backend startup, mark any batch left running or ingesting with an old heartbeat as stalled.
    """
    stall_minutes = int(os.getenv("STALL_MINUTES", "15"))
    catalog = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
    logger.info("Checking for stalled runs (threshold: %d minutes)...", stall_minutes)

    try:
        conn = get_databricks_connection(catalog=catalog)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE `{catalog}`.`platform`.`pipeline_status`
                SET status = 'stalled',
                    failure_next_step = 'Retry from the failed stage',
                    updated_at = current_timestamp()
                WHERE status IN ('running', 'ingesting', 'silver_running', 'gold_running')
                  AND (
                      last_heartbeat_at IS NULL AND created_at < (current_timestamp() - INTERVAL {stall_minutes} MINUTES)
                      OR
                      last_heartbeat_at < (current_timestamp() - INTERVAL {stall_minutes} MINUTES)
                  )
                """
            )
            # Fetch count
            cur.execute(
                f"""
                SELECT count(*) FROM `{catalog}`.`platform`.`pipeline_status`
                WHERE status = 'stalled'
                """
            )
            stalled_cnt = cur.fetchone()[0]
            logger.info("Stalled run check complete. Total stalled: %d", stalled_cnt)
            return stalled_cnt
    except Exception as e:
        logger.warning("Failed to check for stalled runs on startup: %s", e)
        return 0
