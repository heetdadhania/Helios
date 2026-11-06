import json
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    from databricks.sql.client import Connection, Cursor
except ImportError:
    Connection = Any  # type: ignore
    Cursor = Any  # type: ignore

from app.core.config import settings
from pipeline.schema_inference.column_matcher import (
    DEFAULT_SIMILARITY_THRESHOLD,
    match_columns_to_template,
)
from pipeline.schema_inference.template_definitions import (
    KNOWN_TEMPLATES,
    TEMPLATE_ORDERS,
    TEMPLATE_SHIPPING,
)
from pipeline.schema_inference.type_detector import infer_column_type

logger = logging.getLogger("helios.pipeline.schema_inference")

CONFIDENCE_THRESHOLD_REVIEW: float = 0.70


def infer_types_for_records(
    records: List[Dict[str, Any]], sample_size: int = 100
) -> Dict[str, str]:
    """
    Extracts column names across all records and infers their data type
    using sample values from records.
    """
    if not records:
        return {}

    # Collect distinct columns
    col_values: Dict[str, List[Any]] = {}
    for row in records[:sample_size]:
        if isinstance(row, dict):
            for col, val in row.items():
                col_values.setdefault(col, []).append(val)

    inferred: Dict[str, str] = {}
    for col, values in col_values.items():
        inferred[col] = infer_column_type(values)

    return inferred


def score_template_fit(
    incoming_columns: List[str],
    template: Dict[str, Any],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Tuple[float, Dict[str, Optional[Dict[str, Any]]]]:
    """
    Evaluates how closely incoming columns match a given template.
    Returns:
        (confidence_score between 0.0 and 1.0, mapping_dict)
    """
    if not incoming_columns:
        return 0.0, {}

    matches = match_columns_to_template(incoming_columns, template, threshold=threshold)

    template_fields = template.get("fields", {})
    required_fields = template.get("required_fields", [])

    matched_targets = {
        m["target_field"] for m in matches.values() if m is not None and "target_field" in m
    }

    # Evaluate required fields: count mapped and their match strength
    req_match_scores: List[float] = []
    for req in required_fields:
        col_scores = [
            (m["score"] / 100.0)
            for m in matches.values()
            if m is not None and m.get("target_field") == req
        ]
        req_match_scores.append(max(col_scores, default=0.0))

    req_count = len(required_fields)
    matched_req_count = sum(1 for s in req_match_scores if s > 0)
    req_coverage = (matched_req_count / req_count) if req_count else 1.0
    avg_req_score = (sum(req_match_scores) / req_count) if req_count else 1.0

    # Total field coverage
    field_coverage = len(matched_targets) / len(template_fields) if template_fields else 0.0

    # Average match similarity for all matched columns
    valid_scores = [m["score"] for m in matches.values() if m is not None and "score" in m]
    avg_score_ratio = (sum(valid_scores) / (len(valid_scores) * 100.0)) if valid_scores else 0.0

    # Confidence score calculation:
    # A file with unmapped required fields cannot score high (penalized by req_coverage squared)
    if req_coverage < 1.0:
        score = (0.7 * avg_req_score + 0.15 * field_coverage + 0.15 * avg_score_ratio) * (req_coverage ** 2)
    else:
        score = 0.5 * avg_req_score + 0.3 * field_coverage + 0.2 * avg_score_ratio

    clamped_score = max(0.0, min(1.0, score))
    return round(clamped_score, 3), matches


def _update_pipeline_status(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    tenant_id: int,
    stage: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    """Upserts stage and status in platform.pipeline_status."""
    status_table = f"`{catalog}`.`platform`.`pipeline_status`"
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
                batch_id, tenant_id, stage, status, error_message, created_at, updated_at
            )
            VALUES (
                :batch_id, :tenant_id, :stage, :status, :error_message, current_timestamp(), current_timestamp()
            )
        """
        cursor.execute(
            insert_query,
            {
                "batch_id": batch_id,
                "tenant_id": tenant_id,
                "stage": stage,
                "status": status,
                "error_message": error_message,
            },
        )


def save_inferred_schema(
    cursor: Cursor,
    catalog: str,
    batch_id: str,
    detected_template: str,
    column_mapping: Dict[str, Any],
    confidence_score: float,
) -> None:
    """
    Persists inferred schema metadata to platform.inferred_schema.
    CRITICAL: confirmed_by and confirmed_at are strictly left NULL
    until an SMB owner or admin explicitly confirms the mapping in Module 8.
    """
    schema_table = f"`{catalog}`.`platform`.`inferred_schema`"
    insert_query = f"""
        INSERT INTO {schema_table} (
            batch_id,
            detected_template,
            column_mapping_json,
            confidence_score,
            confirmed_by,
            confirmed_at,
            created_at
        )
        VALUES (
            :batch_id,
            :detected_template,
            :column_mapping_json,
            :confidence_score,
            NULL,
            NULL,
            current_timestamp()
        )
    """
    params = {
        "batch_id": batch_id,
        "detected_template": detected_template,
        "column_mapping_json": json.dumps(column_mapping),
        "confidence_score": confidence_score,
    }
    cursor.execute(insert_query, params)


def _acquire_cursor_context(cursor: Optional[Cursor], catalog: str) -> tuple[Cursor, Optional[Connection]]:
    """Acquires the provided cursor or opens a connection to Databricks."""
    if cursor is not None:
        return cursor, None

    try:
        from app.db.base import get_databricks_connection
        conn = get_databricks_connection(catalog=catalog)
        return conn.cursor(), conn
    except Exception as exc:
        logger.error("Failed to acquire Databricks cursor context: %s", exc)
        raise RuntimeError(f"Database connection could not be established: {exc}") from exc


def infer_schema_for_batch(
    batch_id: str,
    tenant_id: int,
    records: List[Dict[str, Any]],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    catalog: Optional[str] = None,
    cursor: Optional[Cursor] = None,
) -> Dict[str, Any]:
    """
    Orchestrates schema inference for a Bronze-loaded batch:
    1. Sets platform.pipeline_status stage='schema_inference', status='schema_inference_running'.
    2. Infers data types for all incoming columns using sample values and regex rules.
    3. Evaluates fit against known templates (Orders vs Shipping).
    4. Calculates overall confidence score (0.0 to 1.0).
    5. Flags for human review if confidence_score < 0.7.
    6. Persists schema mapping to platform.inferred_schema (with confirmed_by=NULL).
    7. Updates platform.pipeline_status status to 'awaiting_confirmation'.
    """
    catalog = catalog or getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
    active_cursor, owned_conn = _acquire_cursor_context(cursor, catalog)

    try:
        # Step 1: Update status to schema_inference_running
        _update_pipeline_status(
            cursor=active_cursor,
            catalog=catalog,
            batch_id=batch_id,
            tenant_id=tenant_id,
            stage="schema_inference",
            status="schema_inference_running",
        )

        # Step 2: Infer types
        inferred_types = infer_types_for_records(records)
        incoming_columns = list(inferred_types.keys())

        # Step 3: Match against templates
        best_template_name: str = "template_orders"
        best_score: float = -1.0
        best_matches: Dict[str, Optional[Dict[str, Any]]] = {}

        for t_name, template in KNOWN_TEMPLATES.items():
            score, matches = score_template_fit(incoming_columns, template, threshold=threshold)
            if score > best_score:
                best_score = score
                best_template_name = t_name
                best_matches = matches

        selected_template = KNOWN_TEMPLATES[best_template_name]
        template_fields = selected_template.get("fields", {})

        # Step 4: Build detailed column mapping
        column_mapping: Dict[str, Any] = {}
        for col in incoming_columns:
            match = best_matches.get(col)
            target_field = match["target_field"] if match else None
            column_mapping[col] = {
                "incoming_column": col,
                "inferred_type": inferred_types.get(col, "string"),
                "target_field": target_field,
                "similarity_score": match["score"] if match else 0.0,
                "target_type": template_fields[target_field]["type"] if target_field else None,
                "is_exact": match.get("is_exact", False) if match else False,
                "matched_alias": match.get("matched_alias") if match else None,
            }

        # Step 5: Flag for review if confidence < 0.70
        flagged_for_review = best_score < CONFIDENCE_THRESHOLD_REVIEW

        # Step 6: Persist inferred schema (Never auto-confirm)
        save_inferred_schema(
            cursor=active_cursor,
            catalog=catalog,
            batch_id=batch_id,
            detected_template=best_template_name,
            column_mapping=column_mapping,
            confidence_score=best_score,
        )

        # Step 7: Update pipeline status to awaiting_confirmation
        _update_pipeline_status(
            cursor=active_cursor,
            catalog=catalog,
            batch_id=batch_id,
            tenant_id=tenant_id,
            stage="schema_inference",
            status="awaiting_confirmation",
        )

        logger.info(
            "Schema inference complete for batch %s: template=%s, score=%.3f, flagged=%s",
            batch_id,
            best_template_name,
            best_score,
            flagged_for_review,
        )

        return {
            "batch_id": batch_id,
            "tenant_id": tenant_id,
            "detected_template": best_template_name,
            "confidence_score": best_score,
            "flagged_for_review": flagged_for_review,
            "column_mapping": column_mapping,
            "status": "awaiting_confirmation",
        }

    except Exception as exc:
        logger.exception("Schema inference failed for batch %s: %s", batch_id, exc)
        try:
            _update_pipeline_status(
                cursor=active_cursor,
                catalog=catalog,
                batch_id=batch_id,
                tenant_id=tenant_id,
                stage="schema_inference",
                status="failed",
                error_message=str(exc),
            )
        except Exception as update_err:
            logger.error("Failed to set failure status for batch %s: %s", batch_id, update_err)
        raise exc

    finally:
        if owned_conn is not None:
            try:
                active_cursor.close()
                owned_conn.close()
            except Exception:
                pass


def run_schema_inference_task(batch_id: str, tenant_id: int, catalog: str = "helios") -> Dict[str, Any]:
    """Task runner query sample records from Bronze table and running schema inference."""
    active_cursor, owned_conn = _acquire_cursor_context(None, catalog)
    try:
        records: List[Dict[str, Any]] = []
        try:
            query = f"SELECT raw_payload FROM `{catalog}`.`bronze`.`raw_transactions` WHERE batch_id = :batch_id LIMIT 100"
            active_cursor.execute(query, {"batch_id": batch_id})
            rows = active_cursor.fetchall()
            if rows:
                for r in rows:
                    raw = r[0]
                    if isinstance(raw, str):
                        try:
                            records.append(json.loads(raw))
                        except Exception:
                            pass
                    elif isinstance(raw, dict):
                        records.append(raw)
        except Exception:
            pass

        return infer_schema_for_batch(
            batch_id=batch_id,
            tenant_id=tenant_id,
            records=records,
            catalog=catalog,
            cursor=active_cursor,
        )
    finally:
        if owned_conn is not None:
            try:
                active_cursor.close()
                owned_conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Helios Schema Inference Task (Module 7)")
    parser.add_argument("--tenant-id", type=int, required=True, help="Tenant ID")
    parser.add_argument("--batch-id", type=str, required=True, help="Batch ID")
    parser.add_argument("--catalog", type=str, default="helios", help="Databricks Unity Catalog name")
    args = parser.parse_args()

    run_schema_inference_task(
        batch_id=args.batch_id,
        tenant_id=args.tenant_id,
        catalog=args.catalog,
    )

