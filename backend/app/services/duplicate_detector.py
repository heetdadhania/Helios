import csv
import hashlib
import io
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from fastapi import HTTPException, status

logger = logging.getLogger("helios.duplicate_detector")

ORDER_ID_ALIASES = {
    "order_id",
    "order id",
    "order_number",
    "order_no",
    "ord_id",
    "ord_no",
    "orderid",
    "id",
}


class DuplicateSubmissionException(HTTPException):
    """Specific 409 exception for duplicate submissions with structured conflict data."""

    def __init__(
        self,
        matched: str,
        submitted_by: str,
        submitted_at: str,
        batch_id: str,
        overlapping_rows: int,
    ) -> None:
        detail_dict = {
            "message": f"Duplicate submission detected: {matched}",
            "matched": matched,
            "submitted_by": submitted_by,
            "submitted_at": submitted_at,
            "batch_id": batch_id,
            "overlapping_rows": overlapping_rows,
        }
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail_dict,
        )
        self.conflict_data = detail_dict


class DuplicateDetector:
    """Service to detect identical submissions, compute hashes, and audit overrides."""

    @staticmethod
    def compute_file_hash(content: bytes) -> str:
        """Compute SHA-256 hash of raw file content."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def compute_rows_hash(records: List[Dict[str, Any]]) -> str:
        """
        Compute SHA-256 hash for database sync and API push records in a fixed order and format.
        Serializes each row into deterministic JSON with sorted keys.
        """
        canonical_rows = [
            json.dumps(
                dict(sorted((str(k), "" if v is None else str(v)) for k, v in r.items())),
                separators=(",", ":"),
            )
            for r in records
        ]
        payload = "\n".join(canonical_rows).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def extract_order_ids_from_records(records: List[Dict[str, Any]]) -> List[str]:
        """Extract order identifiers from structured records."""
        order_ids: List[str] = []
        for r in records:
            for k, v in r.items():
                if str(k).strip().lower() in ORDER_ID_ALIASES and v is not None and str(v).strip():
                    order_ids.append(str(v).strip())
                    break
        return list(dict.fromkeys(order_ids))

    @classmethod
    def extract_order_ids_from_file(cls, content: bytes, filename: str) -> Tuple[List[str], int]:
        """
        Extract order IDs and total data row count from CSV or Excel file bytes.
        Returns: (list_of_unique_order_ids, total_data_rows)
        """
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "csv"
        if ext == "xlsx":
            try:
                wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
                sheet = wb.active
                if sheet is None:
                    return [], 0
                rows_iter = sheet.iter_rows(values_only=True)
                header = None
                for r in rows_iter:
                    if any(c is not None and str(c).strip() for c in r):
                        header = [str(c).strip().lower() if c is not None else "" for c in r]
                        break
                if not header:
                    wb.close()
                    return [], 0

                target_idx = None
                for idx, col in enumerate(header):
                    if col in ORDER_ID_ALIASES:
                        target_idx = idx
                        break

                order_ids: List[str] = []
                total_rows = 0
                for r in rows_iter:
                    if any(c is not None and str(c).strip() for c in r):
                        total_rows += 1
                        if target_idx is not None and len(r) > target_idx:
                            val = r[target_idx]
                            if val is not None and str(val).strip():
                                order_ids.append(str(val).strip())
                wb.close()
                return list(dict.fromkeys(order_ids)), total_rows
            except Exception as e:
                logger.warning("Failed to extract order IDs from xlsx: %s", e)
                return [], 0

        # CSV handling
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="ignore")

        reader = csv.reader(io.StringIO(text))
        header = None
        for r in reader:
            if any(cell.strip() for cell in r):
                header = [cell.strip().lower() for cell in r]
                break

        if not header:
            return [], 0

        target_idx = None
        for idx, col in enumerate(header):
            if col in ORDER_ID_ALIASES:
                target_idx = idx
                break

        order_ids: List[str] = []
        total_rows = 0
        for r in reader:
            if any(cell.strip() for cell in r):
                total_rows += 1
                if target_idx is not None and len(r) > target_idx:
                    val = r[target_idx].strip()
                    if val:
                        order_ids.append(val)

        return list(dict.fromkeys(order_ids)), total_rows

    @classmethod
    def check_and_handle_duplicate(
        cls,
        cursor: Any,
        catalog: str,
        tenant_id: int,
        file_hash: str,
        incoming_order_ids: List[str],
        total_rows: int,
        override_duplicate: bool,
        override_reason: Optional[str],
        acting_user_id: Optional[int],
        acting_user_role: Optional[str],
        new_batch_id: str,
    ) -> None:
        """
        Check for duplicate submissions for the same tenant.
        1. Same file_hash already submitted (any status except rejected or cancelled).
        2. Incoming order IDs already present in Gold fact_orders.
        If duplicate found:
          - If override_duplicate=true and override_reason >= 5 chars: writes audit_trail and allows.
          - Otherwise: raises HTTP 409 with conflict details.
        """
        hash_match_info = None
        gold_match_info = None

        # -------------------------------------------------------------
        # CHECK 1: Same hash already submitted for this tenant
        # -------------------------------------------------------------
        hash_query = f"""
            SELECT 
                pu.upload_id, 
                pu.file_name, 
                pu.uploaded_by, 
                pu.uploaded_at, 
                ps.batch_id, 
                u.email, 
                u.name
            FROM `{catalog}`.`platform`.`pending_uploads` pu
            LEFT JOIN `{catalog}`.`platform`.`pipeline_status` ps ON pu.upload_id = ps.upload_id
            LEFT JOIN `{catalog}`.`platform`.`users` u ON pu.uploaded_by = u.user_id
            WHERE pu.tenant_id = :tenant_id
              AND pu.file_hash = :file_hash
              AND lower(coalesce(pu.status, '')) NOT IN ('rejected', 'cancelled')
            ORDER BY pu.uploaded_at DESC
            LIMIT 1
        """
        cursor.execute(hash_query, {"tenant_id": tenant_id, "file_hash": file_hash})
        row = cursor.fetchone()
        if row:
            uploader_str = row[5] or row[6] or (f"User ID {row[2]}" if row[2] else "System")
            uploaded_at_str = (
                row[3].isoformat() if hasattr(row[3], "isoformat") else str(row[3])
            )
            batch_id_str = row[4] or f"upload-{row[0]}"
            hash_match_info = {
                "matched": "file_hash",
                "submitted_by": uploader_str,
                "submitted_at": uploaded_at_str,
                "batch_id": batch_id_str,
                "overlapping_rows": total_rows,
            }

        # -------------------------------------------------------------
        # CHECK 2: Incoming order IDs already present in Gold fact_orders
        # -------------------------------------------------------------
        if incoming_order_ids:
            # Query for overlapping source_order_ids
            # Escape strings safely for SQL IN clause
            escaped_ids = [str(oid).replace("'", "''") for oid in incoming_order_ids[:1000]]
            in_clause = ", ".join(f"'{oid}'" for oid in escaped_ids)
            gold_query = f"""
                SELECT 
                    fo.source_order_id, 
                    fo.batch_id, 
                    fo.created_at, 
                    ps.upload_id, 
                    pu.uploaded_by, 
                    u.email, 
                    u.name
                FROM `{catalog}`.`gold`.`fact_orders` fo
                LEFT JOIN `{catalog}`.`platform`.`pipeline_status` ps ON fo.batch_id = ps.batch_id
                LEFT JOIN `{catalog}`.`platform`.`pending_uploads` pu ON ps.upload_id = pu.upload_id
                LEFT JOIN `{catalog}`.`platform`.`users` u ON pu.uploaded_by = u.user_id
                WHERE fo.tenant_id = :tenant_id
                  AND fo.source_order_id IN ({in_clause})
            """
            cursor.execute(gold_query, {"tenant_id": tenant_id})
            gold_rows = cursor.fetchall() or []
            if gold_rows:
                matching_order_ids = set(r[0] for r in gold_rows)
                latest_match = gold_rows[0]
                uploader_str = latest_match[5] or latest_match[6] or (f"User ID {latest_match[4]}" if latest_match[4] else "System")
                created_at_str = (
                    latest_match[2].isoformat() if hasattr(latest_match[2], "isoformat") else str(latest_match[2])
                )
                batch_id_str = latest_match[1] or "gold-batch"
                gold_match_info = {
                    "matched": "incoming order IDs already present in Gold",
                    "submitted_by": uploader_str,
                    "submitted_at": created_at_str,
                    "batch_id": batch_id_str,
                    "overlapping_rows": len(matching_order_ids),
                }

        # -------------------------------------------------------------
        # EVALUATE CONFLICT
        # -------------------------------------------------------------
        conflict = None
        if hash_match_info and gold_match_info:
            conflict = {
                "matched": "file_hash and order IDs in Gold",
                "submitted_by": hash_match_info["submitted_by"],
                "submitted_at": hash_match_info["submitted_at"],
                "batch_id": hash_match_info["batch_id"],
                "overlapping_rows": max(hash_match_info["overlapping_rows"], gold_match_info["overlapping_rows"]),
            }
        elif hash_match_info:
            conflict = hash_match_info
        elif gold_match_info:
            conflict = gold_match_info

        if not conflict:
            return  # No duplicate found, proceed normally

        # -------------------------------------------------------------
        # HANDLE DUPLICATE (OVERRIDE OR 409)
        # -------------------------------------------------------------
        if override_duplicate:
            if not override_reason or len(override_reason.strip()) < 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="override_reason must be at least 5 characters.",
                )

            # Write audit_trail record
            audit_table = f"`{catalog}`.`meta`.`audit_trail`"
            audit_query = f"""
                INSERT INTO {audit_table} (
                    actor_user_id, actor_role, action, tenant_id, batch_id, reason, details_json, occurred_at
                )
                VALUES (
                    :actor_user_id, :actor_role, 'duplicate_override', :tenant_id, :batch_id, :reason, :details_json, current_timestamp()
                )
            """
            details_json = json.dumps({
                "matched": conflict["matched"],
                "prior_batch_id": conflict["batch_id"],
                "prior_submitted_by": conflict["submitted_by"],
                "prior_submitted_at": conflict["submitted_at"],
                "overlapping_rows": conflict["overlapping_rows"],
                "file_hash": file_hash,
            })
            params = {
                "actor_user_id": acting_user_id,
                "actor_role": acting_user_role or "system",
                "tenant_id": tenant_id,
                "batch_id": new_batch_id,
                "reason": override_reason.strip(),
                "details_json": details_json,
            }
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    cursor.execute(audit_query, params)
                    break
                except Exception as exc:
                    if "DELTA_METADATA_CHANGED" in str(exc) and attempt < max_retries - 1:
                        logger.warning("Delta concurrency conflict writing audit_trail, retrying (%d/%d)...", attempt + 1, max_retries)
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    raise
            logger.info(
                "Duplicate submission overridden for tenant %d (new_batch=%s, matched=%s, reason=%s)",
                tenant_id,
                new_batch_id,
                conflict["matched"],
                override_reason.strip(),
            )
            return

        # Raise 409 Conflict with structured metadata
        raise DuplicateSubmissionException(
            matched=conflict["matched"],
            submitted_by=conflict["submitted_by"],
            submitted_at=conflict["submitted_at"],
            batch_id=conflict["batch_id"],
            overlapping_rows=conflict["overlapping_rows"],
        )
