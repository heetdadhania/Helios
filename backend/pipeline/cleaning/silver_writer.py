import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

logger = logging.getLogger("helios.pipeline.cleaning.writer")


def _to_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _format_sql_str(v: Optional[Any]) -> str:
    if v is None:
        return "NULL"
    s = str(v).replace("'", "''")
    return f"'{s}'"


def _format_sql_num(v: Optional[Any], default: str = "NULL") -> str:
    if v is None:
        return default
    return str(v)


def _format_sql_ts(v: Optional[Any]) -> str:
    if v is None:
        return "NULL"
    s = str(v).replace("'", "''")
    return f"cast('{s}' as timestamp)"


def _write_orders_clean_chunk(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    tenant_id: int,
    records: List[Dict[str, Any]],
) -> int:
    """Upsert valid cleaned orders into silver.orders_clean using MERGE on (tenant_id, order_id, product_id)."""
    if not records:
        return 0

    table = f"`{catalog}`.`silver`.`orders_clean`"

    # Deduplicate within this chunk on natural key (order_id, product_id) to avoid Delta merge collision
    seen_keys: set[tuple[str, str]] = set()
    deduped_records: List[Dict[str, Any]] = []
    for r in records:
        oid = str(r.get("order_id", "")).strip()
        pid = str(r.get("product_id", "")).strip() if r.get("product_id") is not None else ""
        k = (oid, pid)
        if k not in seen_keys:
            seen_keys.add(k)
            deduped_records.append(r)

    select_clauses: List[str] = []
    for r in deduped_records:
        oid = str(r.get("order_id", ""))
        cid = str(r.get("customer_id", "")) if r.get("customer_id") is not None else None
        pid = str(r.get("product_id", "")) if r.get("product_id") is not None else None
        odt = r.get("order_date")
        qty = int(r.get("quantity", 1))
        uprice = _to_float(r.get("unit_price"))
        tot = _to_float(r.get("total"))
        disc = _to_float(r.get("discount")) or 0.0
        cname = str(r.get("customer_name", "")) if r.get("customer_name") is not None else None
        seg = str(r.get("segment", "")) if r.get("segment") is not None else None
        pname = str(r.get("product_name", "")) if r.get("product_name") is not None else None
        cat = str(r.get("category", "")) if r.get("category") is not None else None
        profit = _to_float(r.get("profit"))

        select_clauses.append(
            f"""SELECT
                cast({tenant_id} as bigint) AS tenant_id,
                {_format_sql_str(batch_id)} AS batch_id,
                {_format_sql_str(oid)} AS order_id,
                {_format_sql_str(cid)} AS customer_id,
                {_format_sql_str(pid)} AS product_id,
                {_format_sql_ts(odt)} AS order_date,
                cast({qty} as int) AS quantity,
                cast({_format_sql_num(uprice)} as decimal(18,4)) AS unit_price,
                cast({_format_sql_num(tot)} as decimal(18,4)) AS total,
                cast({disc} as decimal(18,4)) AS discount,
                {_format_sql_str(cname)} AS customer_name,
                {_format_sql_str(seg)} AS segment,
                {_format_sql_str(pname)} AS product_name,
                {_format_sql_str(cat)} AS category,
                cast({_format_sql_num(profit)} as decimal(18,4)) AS profit,
                true AS is_valid,
                cast(NULL as string) AS rejection_reason,
                current_timestamp() AS processed_at"""
        )

    union_sql = "\nUNION ALL\n".join(select_clauses)

    merge_query = f"""
        MERGE INTO {table} AS target
        USING (
            {union_sql}
        ) AS source
        ON target.tenant_id = source.tenant_id
           AND target.order_id = source.order_id
           AND coalesce(target.product_id, '') = coalesce(source.product_id, '')
        WHEN MATCHED THEN
            UPDATE SET
                target.batch_id = source.batch_id,
                target.customer_id = source.customer_id,
                target.order_date = source.order_date,
                target.quantity = source.quantity,
                target.unit_price = source.unit_price,
                target.total = source.total,
                target.discount = source.discount,
                target.customer_name = source.customer_name,
                target.segment = source.segment,
                target.product_name = source.product_name,
                target.category = source.category,
                target.profit = source.profit,
                target.is_valid = source.is_valid,
                target.rejection_reason = source.rejection_reason,
                target.processed_at = source.processed_at
        WHEN NOT MATCHED THEN
            INSERT (
                tenant_id, batch_id, order_id, customer_id, product_id,
                order_date, quantity, unit_price, total, discount,
                customer_name, segment, product_name, category, profit,
                is_valid, rejection_reason, processed_at
            )
            VALUES (
                source.tenant_id, source.batch_id, source.order_id, source.customer_id, source.product_id,
                source.order_date, source.quantity, source.unit_price, source.total, source.discount,
                source.customer_name, source.segment, source.product_name, source.category, source.profit,
                source.is_valid, source.rejection_reason, source.processed_at
            )
    """

    cursor.execute(merge_query, {})
    return len(records)


def _write_shipping_clean_chunk(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    tenant_id: int,
    records: List[Dict[str, Any]],
) -> int:
    """Upsert valid cleaned shipping rows into silver.shipping_clean using MERGE on (tenant_id, order_id)."""
    if not records:
        return 0

    table = f"`{catalog}`.`silver`.`shipping_clean`"

    seen_keys: set[str] = set()
    deduped_records: List[Dict[str, Any]] = []
    for r in records:
        oid = str(r.get("order_id", "")).strip()
        if oid not in seen_keys:
            seen_keys.add(oid)
            deduped_records.append(r)

    select_clauses: List[str] = []
    for r in deduped_records:
        oid = str(r.get("order_id", ""))
        smode = str(r.get("shipping_mode", "Standard"))
        dstatus = str(r.get("delivery_status", "Unknown"))
        sdate = r.get("scheduled_date") or r.get("shipped_at")
        adate = r.get("actual_date") or r.get("delivered_at")
        sdays = int(r["shipping_days"]) if r.get("shipping_days") is not None else None

        select_clauses.append(
            f"""SELECT
                cast({tenant_id} as bigint) AS tenant_id,
                {_format_sql_str(batch_id)} AS batch_id,
                {_format_sql_str(oid)} AS order_id,
                {_format_sql_str(smode)} AS shipping_mode,
                {_format_sql_str(dstatus)} AS delivery_status,
                {_format_sql_ts(sdate)} AS scheduled_date,
                {_format_sql_ts(adate)} AS actual_date,
                cast({_format_sql_num(sdays)} as int) AS shipping_days,
                true AS is_valid,
                cast(NULL as string) AS rejection_reason,
                current_timestamp() AS processed_at"""
        )

    union_sql = "\nUNION ALL\n".join(select_clauses)

    merge_query = f"""
        MERGE INTO {table} AS target
        USING (
            {union_sql}
        ) AS source
        ON target.tenant_id = source.tenant_id
           AND target.order_id = source.order_id
        WHEN MATCHED THEN
            UPDATE SET
                target.batch_id = source.batch_id,
                target.shipping_mode = source.shipping_mode,
                target.delivery_status = source.delivery_status,
                target.scheduled_date = source.scheduled_date,
                target.actual_date = source.actual_date,
                target.shipping_days = source.shipping_days,
                target.is_valid = source.is_valid,
                target.rejection_reason = source.rejection_reason,
                target.processed_at = source.processed_at
        WHEN NOT MATCHED THEN
            INSERT (
                tenant_id, batch_id, order_id, shipping_mode, delivery_status,
                scheduled_date, actual_date, shipping_days,
                is_valid, rejection_reason, processed_at
            )
            VALUES (
                source.tenant_id, source.batch_id, source.order_id, source.shipping_mode, source.delivery_status,
                source.scheduled_date, source.actual_date, source.shipping_days,
                source.is_valid, source.rejection_reason, source.processed_at
            )
    """

    cursor.execute(merge_query, {})
    return len(records)


def _log_data_quality_rejections(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    tenant_id: int,
    target_table: str,
    rejected_records: List[Dict[str, Any]],
) -> int:
    """Log all rejected records to meta.data_quality_log with explicit failure reasons.

    The rejection_reason already embeds original_value where applicable
    (e.g. 'invalid_quantity: ... (original_value: -3)').
    """
    if not rejected_records:
        return 0

    table = f"`{catalog}`.`meta`.`data_quality_log`"
    query = f"""
        INSERT INTO {table} (
            batch_id, tenant_id, table_name, row_identifier, rejection_reason, logged_at
        )
        VALUES (
            :batch_id, :tenant_id, :table_name, :row_identifier, :rejection_reason, current_timestamp()
        )
    """

    for r in rejected_records:
        row_id = str(r.get("order_id") or r.get("shipment_id") or r.get("tracking_number") or "unknown_row")
        reason = str(r.get("rejection_reason", "unspecified_validation_failure"))
        cursor.execute(
            query,
            {
                "batch_id": batch_id,
                "tenant_id": tenant_id,
                "table_name": target_table,
                "row_identifier": row_id,
                "rejection_reason": reason,
            },
        )

    return len(rejected_records)


def write_silver_records(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    tenant_id: int,
    template_name: str,
    valid_records: List[Dict[str, Any]],
    rejected_records: List[Dict[str, Any]],
) -> Dict[str, int]:
    """
    Persist valid cleaned records into target Silver table via MERGE and log
    rejected rows into meta.data_quality_log.
    """
    is_shipping = "ship" in template_name.lower()
    target_table = "silver.shipping_clean" if is_shipping else "silver.orders_clean"

    if is_shipping:
        written_count = _write_shipping_clean_chunk(cursor, catalog, batch_id, tenant_id, valid_records)
    else:
        written_count = _write_orders_clean_chunk(cursor, catalog, batch_id, tenant_id, valid_records)

    logged_rejections = _log_data_quality_rejections(
        cursor=cursor,
        catalog=catalog,
        batch_id=batch_id,
        tenant_id=tenant_id,
        target_table=target_table,
        rejected_records=rejected_records,
    )

    logger.info(
        "Silver write complete for batch %s: valid_written=%d, rejected_logged=%d (table=%s)",
        batch_id,
        written_count,
        logged_rejections,
        target_table,
    )

    return {
        "valid_written": written_count,
        "rejected_logged": logged_rejections,
    }
