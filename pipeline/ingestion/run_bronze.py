import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

try:
    from databricks.sql.client import Connection, Cursor
except ImportError:
    Connection = Any  # type: ignore
    Cursor = Any  # type: ignore

from pipeline.ingestion.bronze_loader import load_bronze_records
from pipeline.ingestion.read_source import detect_target_table, read_source

logger = logging.getLogger("helios.pipeline.run_bronze")


def _record_audit_log(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    stage: str,
    row_count: int,
    status: str,
    started_at: datetime,
    completed_at: datetime,
    error_message: Optional[str] = None,
) -> None:
    """Insert pipeline execution metrics into meta.etl_audit_log."""
    audit_table = f"`{catalog}`.`meta`.`etl_audit_log`"
    query = f"""
        INSERT INTO {audit_table} (
            batch_id, stage, row_count, status, started_at, completed_at, error_message
        )
        VALUES (
            :batch_id, :stage, :row_count, :status, :started_at, :completed_at, :error_message
        )
    """
    params = {
        "batch_id": batch_id,
        "stage": stage,
        "row_count": row_count,
        "status": status,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "error_message": error_message,
    }
    cursor.execute(query, params)


def _update_pipeline_status(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    tenant_id: int,
    stage: str,
    status: str,
    upload_id: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    """Upsert state record in platform.pipeline_status."""
    status_table = f"`{catalog}`.`platform`.`pipeline_status`"

    # Check if batch_id record already exists
    check_query = f"SELECT batch_id FROM {status_table} WHERE batch_id = :batch_id LIMIT 1"
    cursor.execute(check_query, {"batch_id": batch_id})
    existing = cursor.fetchone()

    if existing:
        update_query = f"""
            UPDATE {status_table}
            SET stage = :stage,
                status = :status,
                error_message = :error_message,
                updated_at = current_timestamp()
            WHERE batch_id = :batch_id
        """
        cursor.execute(
            update_query,
            {"batch_id": batch_id, "stage": stage, "status": status, "error_message": error_message},
        )
    else:
        insert_query = f"""
            INSERT INTO {status_table} (
                batch_id, tenant_id, upload_id, stage, status, error_message, created_at, updated_at
            )
            VALUES (
                :batch_id, :tenant_id, :upload_id, :stage, :status, :error_message, current_timestamp(), current_timestamp()
            )
        """
        cursor.execute(
            insert_query,
            {
                "batch_id": batch_id,
                "tenant_id": tenant_id,
                "upload_id": upload_id,
                "stage": stage,
                "status": status,
                "error_message": error_message,
            },
        )


def _acquire_cursor_context(cursor: Optional[Cursor], catalog: str) -> tuple[Cursor, Optional[Connection]]:
    """Acquire existing cursor or establish a new Databricks connection."""
    if cursor is not None:
        return cursor, None

    try:
        from app.db.base import get_databricks_connection
        conn = get_databricks_connection(catalog=catalog)
        return conn.cursor(), conn
    except Exception as exc:
        logger.error("Failed to establish default Databricks connection: %s", exc)
        raise RuntimeError(f"Database connection could not be established: {exc}") from exc


def run_bronze_ingestion(
    tenant_id: int,
    batch_id: str,
    source_type: str,
    data: Any,
    target_table: Optional[str] = None,
    upload_id: Optional[int] = None,
    catalog: str = "helios",
    cursor: Optional[Cursor] = None,
) -> Dict[str, Any]:
    """
    Unified entry point orchestrating Medallion Bronze ingestion for all channels.
    
    Normalizes raw source data, writes to bronze Delta tables, updates pipeline_status,
    and logs duration metrics to meta.etl_audit_log.
    """
    started_at = datetime.now(timezone.utc)
    start_perf = time.perf_counter()
    active_cursor, owned_conn = _acquire_cursor_context(cursor, catalog)
    records_count = 0

    try:
        # 1. Normalize input data into in-memory dictionaries
        records = read_source(data)
        records_count = len(records)

        # 2. Determine target table (raw_orders or raw_shipping)
        resolved_table = target_table or detect_target_table(records)

        # 3. Load records into Bronze table
        loaded_count = load_bronze_records(
            cursor=active_cursor,
            tenant_id=tenant_id,
            batch_id=batch_id,
            source_type=source_type,
            records=records,
            target_table=resolved_table,
            catalog=catalog,
        )

        # 4. Update pipeline_status to 'ingested'
        _update_pipeline_status(
            cursor=active_cursor,
            catalog=catalog,
            batch_id=batch_id,
            tenant_id=tenant_id,
            stage="bronze_ingest",
            status="ingested",
            upload_id=upload_id,
        )

        # 5. Record successful run in meta.etl_audit_log
        completed_at = datetime.now(timezone.utc)
        duration_sec = time.perf_counter() - start_perf

        _record_audit_log(
            cursor=active_cursor,
            catalog=catalog,
            batch_id=batch_id,
            stage="bronze_ingest",
            row_count=loaded_count,
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
        )

        logger.info(
            "Bronze ingestion completed for batch %s in %.2fs (%d rows)",
            batch_id,
            duration_sec,
            loaded_count,
        )

        return {
            "batch_id": batch_id,
            "tenant_id": tenant_id,
            "target_table": resolved_table,
            "source_type": source_type,
            "records_loaded": loaded_count,
            "status": "ingested",
            "duration_seconds": round(duration_sec, 3),
        }

    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        err_msg = str(exc)
        logger.exception("Bronze ingestion failed for batch %s: %s", batch_id, err_msg)

        try:
            # Update pipeline_status to 'failed' (stage='bronze')
            _update_pipeline_status(
                cursor=active_cursor,
                catalog=catalog,
                batch_id=batch_id,
                tenant_id=tenant_id,
                stage="bronze",
                status="failed",
                upload_id=upload_id,
                error_message=err_msg,
            )

            # Record failure in meta.etl_audit_log
            _record_audit_log(
                cursor=active_cursor,
                catalog=catalog,
                batch_id=batch_id,
                stage="bronze_ingest",
                row_count=records_count,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                error_message=err_msg,
            )
        except Exception as update_err:
            logger.error("Failed to persist failure status for batch %s: %s", batch_id, update_err)

        raise exc

    finally:
        if owned_conn is not None:
            try:
                active_cursor.close()
                owned_conn.close()
            except Exception:
                pass
