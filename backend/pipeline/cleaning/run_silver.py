import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    from databricks.sql.client import Connection, Cursor
except ImportError:
    Connection = Any  # type: ignore
    Cursor = Any  # type: ignore

from app.core.config import settings
from pipeline.cleaning.currency_cleaner import clean_currency_fields
from pipeline.cleaning.date_standardizer import standardize_date_fields
from pipeline.cleaning.dedup import deduplicate_records
from pipeline.cleaning.null_handler import handle_nulls
from pipeline.cleaning.silver_writer import write_silver_records

logger = logging.getLogger("helios.pipeline.cleaning.run_silver")


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
    error_message: Optional[str] = None,
) -> None:
    """Update batch lifecycle state in platform.pipeline_status."""
    status_table = f"`{catalog}`.`platform`.`pipeline_status`"
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


def _acquire_cursor_context(cursor: Optional[Cursor], catalog: str) -> tuple[Cursor, Optional[Connection]]:
    """Acquire existing cursor or establish a new Databricks connection."""
    if cursor is not None:
        return cursor, None

    try:
        from app.db.base import get_databricks_connection
        conn = get_databricks_connection(catalog=catalog)
        return conn.cursor(), conn
    except Exception as exc:
        logger.error("Failed to acquire Databricks cursor: %s", exc)
        raise RuntimeError(f"Database connection could not be established: {exc}") from exc


def _fetch_bronze_records(cursor: Cursor, catalog: str, batch_id: str) -> Tuple[List[Dict[str, Any]], str]:
    """Read Bronze raw rows by batch_id from raw_orders or raw_shipping."""
    orders_table = f"`{catalog}`.`bronze`.`raw_orders`"
    cursor.execute(f"SELECT raw_row_json FROM {orders_table} WHERE batch_id = :batch_id", {"batch_id": batch_id})
    rows = cursor.fetchall() or []
    detected_template = "template_orders"

    if not rows:
        shipping_table = f"`{catalog}`.`bronze`.`raw_shipping`"
        cursor.execute(f"SELECT raw_row_json FROM {shipping_table} WHERE batch_id = :batch_id", {"batch_id": batch_id})
        rows = cursor.fetchall() or []
        detected_template = "template_shipping"

    records: List[Dict[str, Any]] = []
    for r in rows:
        raw_json = r[0]
        try:
            records.append(json.loads(raw_json) if isinstance(raw_json, str) else raw_json)
        except Exception:
            records.append({"raw": str(raw_json)})

    return records, detected_template


def _remap_record(raw_row: Dict[str, Any], column_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Remap incoming raw column names to canonical target fields."""
    mapped: Dict[str, Any] = {}
    for raw_col, val in raw_row.items():
        if raw_col in column_mapping:
            mapping_def = column_mapping[raw_col]
            target_field = (
                mapping_def.get("target_field")
                if isinstance(mapping_def, dict)
                else str(mapping_def)
            )
            if target_field and str(target_field).lower() not in ("__ignore__", "ignore", "ignore this column"):
                mapped[target_field] = val
            elif not target_field:
                mapped[raw_col] = val
        else:
            mapped[raw_col] = val
    return mapped


def run_silver_pipeline(
    batch_id: str,
    catalog: Optional[str] = None,
    cursor: Optional[Cursor] = None,
) -> Dict[str, Any]:
    """
    Orchestrates the Medallion Silver transformation:
    1. Reads Bronze raw records and confirmed schema mapping.
    2. Maps column names to canonical fields.
    3. Cleans currency and formats timestamps.
    4. Handles nulls/imputations and drops/flags invalid records.
    5. Deduplicates by natural key (order_id).
    6. Writes valid clean rows to silver.orders_clean or silver.shipping_clean.
    7. Logs all rejected rows to meta.data_quality_log.
    8. Updates platform.pipeline_status to 'gold_running' and logs to meta.etl_audit_log.
    """
    catalog = catalog or getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
    started_at = datetime.now(timezone.utc)
    start_perf = time.perf_counter()
    active_cursor, owned_conn = _acquire_cursor_context(cursor, catalog)

    tenant_id: int = 1
    template_name: str = "template_orders"

    try:
        # Step 1: Read batch metadata and confirmed mapping
        status_table = f"`{catalog}`.`platform`.`pipeline_status`"
        inferred_table = f"`{catalog}`.`platform`.`inferred_schema`"

        query = f"""
            SELECT ps.tenant_id, inf.detected_template, inf.column_mapping_json
            FROM {status_table} ps
            LEFT JOIN {inferred_table} inf ON ps.batch_id = inf.batch_id
            WHERE ps.batch_id = :batch_id
            LIMIT 1
        """
        active_cursor.execute(query, {"batch_id": batch_id})
        meta_row = active_cursor.fetchone()

        column_mapping: Dict[str, Any] = {}
        if meta_row:
            tenant_id = int(meta_row[0])
            if meta_row[1]:
                template_name = str(meta_row[1])
            if meta_row[2]:
                try:
                    column_mapping = json.loads(meta_row[2]) if isinstance(meta_row[2], str) else meta_row[2]
                except Exception:
                    column_mapping = {}

        # Step 2: Read Bronze records
        raw_records, bronze_template = _fetch_bronze_records(active_cursor, catalog, batch_id)
        if not meta_row or not meta_row[1]:
            template_name = bronze_template

        # Step 3: Remap columns
        remapped_records = [_remap_record(r, column_mapping) for r in raw_records]

        # Step 4: Cleaning pipeline
        is_shipping = "ship" in template_name.lower()
        currency_fields = ["shipping_cost", "freight_charge"] if is_shipping else ["total", "unit_price", "discount", "total_amount", "profit"]
        date_fields = ["scheduled_date", "actual_date", "shipped_at", "delivered_at"] if is_shipping else ["order_date", "created_at"]

        cleaned_stage1: List[Dict[str, Any]] = []
        rejected_stage1: List[Dict[str, Any]] = []

        for rec in remapped_records:
            raw_orig = dict(rec)
            cur_cleaned, cur_errs = clean_currency_fields(rec, currency_fields)
            if cur_errs:
                err_f = cur_errs[0]
                orig_v = raw_orig.get(err_f)
                cur_cleaned["rejection_reason"] = f"invalid_currency_fields: {err_f} could not be parsed as currency (original_value: {orig_v})"
                rejected_stage1.append(cur_cleaned)
                continue

            date_cleaned, date_errs = standardize_date_fields(cur_cleaned, date_fields)
            if date_errs:
                err_f = date_errs[0]
                orig_v = raw_orig.get(err_f)
                date_cleaned["rejection_reason"] = f"invalid_date_fields: {','.join(date_errs)} (original_value: {orig_v})"
                rejected_stage1.append(date_cleaned)
                continue

            cleaned_stage1.append(date_cleaned)

        # Step 5: Null handling and schema rules
        valid_after_nulls, rejected_nulls = handle_nulls(cleaned_stage1, template_name)

        # Step 6: Deduplication by natural key
        if is_shipping:
            key_fields = ("order_id",)
        else:
            has_product_id = any("product_id" in r and r.get("product_id") for r in valid_after_nulls)
            key_fields = ("order_id", "product_id") if has_product_id else ("order_id",)
        unique_valid, rejected_dupes = deduplicate_records(valid_after_nulls, key_fields=key_fields)

        # Combine all rejections
        all_rejected = rejected_stage1 + rejected_nulls + rejected_dupes

        # Step 7: Write to Silver and log rejections
        write_results = write_silver_records(
            cursor=active_cursor,
            catalog=catalog,
            batch_id=batch_id,
            tenant_id=tenant_id,
            template_name=template_name,
            valid_records=unique_valid,
            rejected_records=all_rejected,
        )

        # Step 8: Update pipeline status to 'gold_running'
        _update_pipeline_status(
            cursor=active_cursor,
            catalog=catalog,
            batch_id=batch_id,
            tenant_id=tenant_id,
            stage="gold_transform",
            status="gold_running",
        )

        # Step 9: Record success in meta.etl_audit_log
        completed_at = datetime.now(timezone.utc)
        duration_sec = time.perf_counter() - start_perf

        _record_audit_log(
            cursor=active_cursor,
            catalog=catalog,
            batch_id=batch_id,
            stage="silver_clean",
            row_count=write_results["valid_written"],
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
        )

        logger.info(
            "Silver pipeline completed for batch %s in %.2fs: clean=%d, rejected=%d",
            batch_id,
            duration_sec,
            write_results["valid_written"],
            write_results["rejected_logged"],
        )

        return {
            "batch_id": batch_id,
            "tenant_id": tenant_id,
            "template": template_name,
            "raw_rows": len(raw_records),
            "clean_rows": write_results["valid_written"],
            "rejected_rows": write_results["rejected_logged"],
            "status": "gold_running",
            "duration_seconds": round(duration_sec, 3),
        }

    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        err_msg = str(exc)
        logger.exception("Silver pipeline failed for batch %s: %s", batch_id, err_msg)

        try:
            _update_pipeline_status(
                cursor=active_cursor,
                catalog=catalog,
                batch_id=batch_id,
                tenant_id=tenant_id,
                stage="silver",
                status="failed",
                error_message=err_msg,
            )
            _record_audit_log(
                cursor=active_cursor,
                catalog=catalog,
                batch_id=batch_id,
                stage="silver_clean",
                row_count=0,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                error_message=err_msg,
            )
        except Exception as update_err:
            logger.error("Failed to record silver failure status for batch %s: %s", batch_id, update_err)

        raise exc

    finally:
        if owned_conn is not None:
            try:
                active_cursor.close()
                owned_conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Helios Silver Cleaning Task (Module 9)")
    parser.add_argument("--tenant-id", type=int, required=False, default=None, help="Tenant ID")
    parser.add_argument("--batch-id", type=str, required=True, help="Batch ID")
    parser.add_argument("--catalog", type=str, default="helios", help="Databricks Unity Catalog name")
    args = parser.parse_args()

    run_silver_pipeline(
        batch_id=args.batch_id,
        tenant_id=args.tenant_id,
        catalog=args.catalog,
    )

