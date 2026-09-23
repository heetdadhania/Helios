import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

logger = logging.getLogger("helios.pipeline.cleaning.writer")


def _write_orders_clean_chunk(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    tenant_id: int,
    records: List[Dict[str, Any]],
) -> int:
    """Insert valid cleaned orders into silver.orders_clean."""
    if not records:
        return 0

    table = f"`{catalog}`.`silver`.`orders_clean`"
    query = f"""
        INSERT INTO {table} (
            tenant_id, batch_id, order_id, customer_id, product_id,
            order_date, quantity, unit_price, total, discount,
            is_valid, rejection_reason, processed_at
        )
        VALUES (
            :tenant_id, :batch_id, :order_id, :customer_id, :product_id,
            :order_date, :quantity, :unit_price, :total, :discount,
            true, NULL, current_timestamp()
        )
    """

    for r in records:
        params = {
            "tenant_id": tenant_id,
            "batch_id": batch_id,
            "order_id": str(r.get("order_id", "")),
            "customer_id": str(r.get("customer_id", "")) if r.get("customer_id") is not None else None,
            "product_id": str(r.get("product_id", "")) if r.get("product_id") is not None else None,
            "order_date": r.get("order_date"),
            "quantity": int(r.get("quantity", 1)),
            "unit_price": float(r.get("unit_price", 0.0)) if r.get("unit_price") is not None else None,
            "total": float(r.get("total", 0.0)) if r.get("total") is not None else None,
            "discount": float(r.get("discount", 0.0)) if r.get("discount") is not None else 0.0,
        }
        cursor.execute(query, params)

    return len(records)


def _write_shipping_clean_chunk(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    tenant_id: int,
    records: List[Dict[str, Any]],
) -> int:
    """Insert valid cleaned shipping rows into silver.shipping_clean."""
    if not records:
        return 0

    table = f"`{catalog}`.`silver`.`shipping_clean`"
    query = f"""
        INSERT INTO {table} (
            tenant_id, batch_id, order_id, shipping_mode, delivery_status,
            scheduled_date, actual_date, shipping_days,
            is_valid, rejection_reason, processed_at
        )
        VALUES (
            :tenant_id, :batch_id, :order_id, :shipping_mode, :delivery_status,
            :scheduled_date, :actual_date, :shipping_days,
            true, NULL, current_timestamp()
        )
    """

    for r in records:
        params = {
            "tenant_id": tenant_id,
            "batch_id": batch_id,
            "order_id": str(r.get("order_id", "")),
            "shipping_mode": str(r.get("shipping_mode", "Standard")),
            "delivery_status": str(r.get("delivery_status", "Unknown")),
            "scheduled_date": r.get("scheduled_date") or r.get("shipped_at"),
            "actual_date": r.get("actual_date") or r.get("delivered_at"),
            "shipping_days": int(r["shipping_days"]) if r.get("shipping_days") is not None else None,
        }
        cursor.execute(query, params)

    return len(records)


def _log_data_quality_rejections(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    tenant_id: int,
    target_table: str,
    rejected_records: List[Dict[str, Any]],
) -> int:
    """Log all rejected records to meta.data_quality_log with explicit failure reasons."""
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
    Persist valid cleaned records into target Silver table and log
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
