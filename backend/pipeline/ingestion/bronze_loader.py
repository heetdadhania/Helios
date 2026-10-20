import json
import logging
from typing import Any, Dict, List, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

logger = logging.getLogger("helios.pipeline.bronze_loader")

BATCH_INSERT_CHUNK_SIZE = 500


def _resolve_full_table_name(target_table: str, catalog: str) -> str:
    """Format catalog and schema qualification for Delta Lake Bronze table."""
    cleaned = target_table.replace("`", "").strip().lower()
    if cleaned.startswith(f"{catalog.lower()}.bronze."):
        table_name = cleaned.split(".")[-1]
    elif cleaned.startswith("bronze."):
        table_name = cleaned.split(".")[-1]
    else:
        table_name = cleaned

    if table_name not in ("raw_orders", "raw_shipping"):
        logger.warning("Unrecognized target table '%s', defaulting to 'raw_orders'", table_name)
        table_name = "raw_orders"

    return f"`{catalog}`.`bronze`.`{table_name}`"


def _insert_chunk(
    cursor: Cursor,
    full_table: str,
    tenant_id: int,
    batch_id: str,
    source_type: str,
    chunk: List[Dict[str, Any]],
) -> None:
    """Insert a chunk of rows into target Bronze Delta table."""
    # Build parameterized multi-row insert statement
    value_clauses: List[str] = []
    params: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "batch_id": batch_id,
        "source_type": source_type,
    }

    for idx, row in enumerate(chunk):
        param_name = f"row_json_{idx}"
        # Preserve raw row as immutable JSON string
        params[param_name] = json.dumps(row, default=str)
        value_clauses.append(
            f"(:tenant_id, :batch_id, :source_type, :{param_name}, current_timestamp())"
        )

    insert_sql = f"""
        INSERT INTO {full_table} (
            tenant_id, batch_id, source_type, raw_row_json, uploaded_at
        )
        VALUES {', '.join(value_clauses)}
    """
    cursor.execute(insert_sql, params)


def load_bronze_records(
    cursor: Cursor,
    tenant_id: int,
    batch_id: str,
    source_type: str,
    records: List[Dict[str, Any]],
    target_table: str = "raw_orders",
    catalog: str = "helios",
) -> int:
    """
    Persist raw records into bronze.raw_orders or bronze.raw_shipping with tracking tags.
    
    Preserves all incoming columns as immutable JSON inside raw_row_json.
    """
    if not records:
        logger.warning("No records to load into Bronze for batch %s", batch_id)
        return 0

    full_table = _resolve_full_table_name(target_table, catalog)
    total_loaded = 0

    logger.info(
        "Loading %d raw records into %s (tenant: %d, batch: %s, source: %s)",
        len(records),
        full_table,
        tenant_id,
        batch_id,
        source_type,
    )

    for i in range(0, len(records), BATCH_INSERT_CHUNK_SIZE):
        chunk = records[i : i + BATCH_INSERT_CHUNK_SIZE]
        _insert_chunk(
            cursor=cursor,
            full_table=full_table,
            tenant_id=tenant_id,
            batch_id=batch_id,
            source_type=source_type,
            chunk=chunk,
        )
        total_loaded += len(chunk)

    logger.info("Successfully loaded %d records into %s", total_loaded, full_table)
    return total_loaded
