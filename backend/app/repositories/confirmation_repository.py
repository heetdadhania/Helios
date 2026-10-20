import json
import logging
from typing import Any, Dict, List, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings

logger = logging.getLogger("helios.repositories.confirmation")


class ConfirmationRepository:
    """Repository handling database operations for schema review, preview, confirmation, and completeness."""

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None):
        self.cursor = cursor
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.pipeline_table = f"`{self.catalog}`.`platform`.`pipeline_status`"
        self.inferred_table = f"`{self.catalog}`.`platform`.`inferred_schema`"
        self.pending_table = f"`{self.catalog}`.`platform`.`pending_uploads`"
        self.team_table = f"`{self.catalog}`.`platform`.`team_assignments`"
        self.raw_orders_table = f"`{self.catalog}`.`bronze`.`raw_orders`"
        self.raw_shipping_table = f"`{self.catalog}`.`bronze`.`raw_shipping`"
        self.clean_orders_table = f"`{self.catalog}`.`silver`.`orders_clean`"
        self.clean_shipping_table = f"`{self.catalog}`.`silver`.`shipping_clean`"
        self.dq_log_table = f"`{self.catalog}`.`meta`.`data_quality_log`"

    def get_pending(
        self,
        user_id: int,
        user_role: str,
        tenant_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all batches in 'awaiting_confirmation' status.
        Admins see all tenants; Team Members see only their assigned tenants.
        """
        is_admin = user_role.lower() == "admin"
        where_clauses = ["ps.status IN ('ingesting', 'pending_review', 'awaiting_confirmation')"]
        params: Dict[str, Any] = {}

        if not is_admin:
            params["user_id"] = user_id

        if tenant_filter and tenant_filter.strip() and tenant_filter.lower() != "all":
            clean_tf = tenant_filter.strip()
            if clean_tf.isdigit():
                where_clauses.append("ps.tenant_id = :tenant_filter_id")
                params["tenant_filter_id"] = int(clean_tf)
            else:
                where_clauses.append("lower(t.business_name) LIKE :tenant_name_like")
                params["tenant_name_like"] = f"%{clean_tf.lower()}%"

        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        if is_admin:
            query = f"""
                SELECT 
                    ps.batch_id,
                    ps.tenant_id,
                    t.business_name AS tenant_name,
                    ps.upload_id,
                    ps.stage,
                    ps.status,
                    ps.created_at,
                    ps.updated_at,
                    inf.detected_template,
                    inf.confidence_score,
                    COALESCE(pu.source_type, 'upload') AS source_type,
                    COALESCE(pu.file_name, 'upload.data') AS filename
                FROM {self.pipeline_table} ps
                LEFT JOIN `{self.catalog}`.`platform`.`tenants` t ON ps.tenant_id = t.tenant_id
                LEFT JOIN {self.inferred_table} inf ON ps.batch_id = inf.batch_id
                LEFT JOIN {self.pending_table} pu ON ps.upload_id = pu.upload_id
                {where_sql}
                ORDER BY ps.created_at DESC
            """
            self.cursor.execute(query, params)
        else:
            query = f"""
                SELECT 
                    ps.batch_id,
                    ps.tenant_id,
                    t.business_name AS tenant_name,
                    ps.upload_id,
                    ps.stage,
                    ps.status,
                    ps.created_at,
                    ps.updated_at,
                    inf.detected_template,
                    inf.confidence_score,
                    COALESCE(pu.source_type, 'upload') AS source_type,
                    COALESCE(pu.file_name, 'upload.data') AS filename
                FROM {self.pipeline_table} ps
                INNER JOIN {self.team_table} ta ON ps.tenant_id = ta.tenant_id AND ta.user_id = :user_id
                LEFT JOIN `{self.catalog}`.`platform`.`tenants` t ON ps.tenant_id = t.tenant_id
                LEFT JOIN {self.inferred_table} inf ON ps.batch_id = inf.batch_id
                LEFT JOIN {self.pending_table} pu ON ps.upload_id = pu.upload_id
                {where_sql}
                ORDER BY ps.created_at DESC
            """
            self.cursor.execute(query, params)

        rows = self.cursor.fetchall() or []
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return [dict(zip(columns, row)) for row in rows]

    def check_user_tenant_access(self, user_id: int, user_role: str, tenant_id: int) -> bool:
        """Verify whether user can view or confirm batches for the given tenant."""
        if user_role.lower() == "admin":
            return True
        if user_role.lower() != "team_member":
            return False

        query = f"""
            SELECT 1 FROM {self.team_table}
            WHERE user_id = :user_id AND tenant_id = :tenant_id
            LIMIT 1
        """
        self.cursor.execute(query, {"user_id": user_id, "tenant_id": tenant_id})
        return self.cursor.fetchone() is not None

    def get_batch_metadata(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Fetch pipeline status and inferred schema record for a given batch."""
        query = f"""
            SELECT 
                ps.batch_id,
                ps.tenant_id,
                ps.upload_id,
                ps.stage,
                ps.status,
                inf.detected_template,
                inf.confidence_score,
                inf.column_mapping_json,
                inf.internal_notes,
                pu.source_type
            FROM {self.pipeline_table} ps
            LEFT JOIN {self.inferred_table} inf ON ps.batch_id = inf.batch_id
            LEFT JOIN {self.pending_table} pu ON ps.upload_id = pu.upload_id
            WHERE ps.batch_id = :batch_id
            LIMIT 1
        """
        self.cursor.execute(query, {"batch_id": batch_id})
        row = self.cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in self.cursor.description]
        return dict(zip(columns, row))

    def _fetch_sample_rows_from_bronze(self, batch_id: str) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch sample rows from Bronze raw tables (checking orders then shipping)."""
        orders_q = f"SELECT raw_row_json, source_type FROM {self.raw_orders_table} WHERE batch_id = :batch_id LIMIT 10"
        self.cursor.execute(orders_q, {"batch_id": batch_id})
        rows = self.cursor.fetchall() or []
        detected_source: Optional[str] = None

        if not rows:
            ship_q = f"SELECT raw_row_json, source_type FROM {self.raw_shipping_table} WHERE batch_id = :batch_id LIMIT 10"
            self.cursor.execute(ship_q, {"batch_id": batch_id})
            rows = self.cursor.fetchall() or []

        samples: List[Dict[str, Any]] = []
        for r in rows:
            raw_json, src = r[0], r[1]
            if not detected_source and src:
                detected_source = str(src)
            try:
                samples.append(json.loads(raw_json) if isinstance(raw_json, str) else raw_json)
            except Exception:
                samples.append({"raw": str(raw_json)})

        return samples, detected_source

    def get_preview(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Consolidate schema mapping, confidence, source type, internal notes, and sample rows for preview."""
        meta = self.get_batch_metadata(batch_id)
        if not meta:
            return None

        samples, bronze_source = self._fetch_sample_rows_from_bronze(batch_id)
        source_type = meta.get("source_type") or bronze_source or "upload"

        mapping_raw = meta.get("column_mapping_json")
        mapping: Dict[str, Any] = {}
        if mapping_raw:
            try:
                mapping = json.loads(mapping_raw) if isinstance(mapping_raw, str) else mapping_raw
            except Exception:
                mapping = {}

        # Determine unmapped required fields for detected template
        from pipeline.schema_inference.template_definitions import get_template
        detected_template_name = meta.get("detected_template") or "template_orders"
        template_obj = get_template(detected_template_name)
        required_fields = template_obj.get("required_fields", [])
        mapped_targets = set()
        for v in mapping.values():
            tf = v.get("target_field") if isinstance(v, dict) else str(v)
            if tf and str(tf).lower() not in ("__ignore__", "ignore", "ignore this column", "null", "none"):
                mapped_targets.add(tf)
        unmapped_required = [req for req in required_fields if req not in mapped_targets]

        return {
            "batch_id": meta["batch_id"],
            "tenant_id": meta["tenant_id"],
            "detected_template": detected_template_name,
            "confidence_score": float(meta.get("confidence_score") or 0.0),
            "source_type": source_type,
            "column_mapping": mapping,
            "sample_rows": samples,
            "internal_notes": meta.get("internal_notes"),
            "unmapped_required_fields": unmapped_required,
        }

    def save_confirmation(
        self,
        batch_id: str,
        confirmed_template: str,
        column_mapping: Dict[str, Any],
        confirmed_by: int,
        internal_notes: Optional[str] = None,
    ) -> None:
        """
        Record schema confirmation, persist updated mapping, internal notes (if provided),
        and transition pipeline to Silver running.
        """
        # 1. Update inferred_schema table
        update_cols = [
            "detected_template = :confirmed_template",
            "column_mapping_json = :column_mapping_json",
            "confirmed_by = :confirmed_by",
            "confirmed_at = current_timestamp()",
        ]
        params: Dict[str, Any] = {
            "batch_id": batch_id,
            "confirmed_template": confirmed_template,
            "column_mapping_json": json.dumps(column_mapping),
            "confirmed_by": confirmed_by,
        }

        if internal_notes is not None:
            update_cols.append("internal_notes = :internal_notes")
            params["internal_notes"] = internal_notes

        update_schema_q = f"""
            UPDATE {self.inferred_table}
            SET {", ".join(update_cols)}
            WHERE batch_id = :batch_id
        """
        self.cursor.execute(update_schema_q, params)

        # 2. Update pipeline_status to running
        update_status_q = f"""
            UPDATE {self.pipeline_table}
            SET stage = 'silver_running',
                status = 'running',
                last_heartbeat_at = current_timestamp(),
                updated_at = current_timestamp()
            WHERE batch_id = :batch_id
        """
        self.cursor.execute(update_status_q, {"batch_id": batch_id})

        # 3. Update pending_uploads if associated
        update_upload_q = f"""
            UPDATE {self.pending_table}
            SET status = 'approved',
                decision = 'approved',
                decided_by = :confirmed_by,
                decided_at = current_timestamp()
            WHERE upload_id IN (
                SELECT upload_id FROM {self.pipeline_table} WHERE batch_id = :batch_id AND upload_id IS NOT NULL
            )
        """
        try:
            self.cursor.execute(update_upload_q, {"batch_id": batch_id, "confirmed_by": confirmed_by})
        except Exception as exc:
            logger.warning("Could not update pending_uploads status for batch %s: %s", batch_id, exc)

    def is_tenant_running_batch(self, tenant_id: int, exclude_batch_id: str) -> bool:
        """Check if any other batch for this tenant is currently executing."""
        q = f"""
            SELECT batch_id FROM {self.pipeline_table}
            WHERE tenant_id = :tenant_id 
              AND status IN ('running', 'silver_running', 'gold_running')
              AND batch_id != :exclude_batch_id
            LIMIT 1
        """
        self.cursor.execute(q, {"tenant_id": tenant_id, "exclude_batch_id": exclude_batch_id})
        row = self.cursor.fetchone()
        return bool(row)

    def write_audit_trail(
        self,
        actor_user_id: Optional[int],
        actor_role: str,
        action: str,
        tenant_id: int,
        batch_id: str,
        reason: Optional[str] = None,
        details_json: Optional[str] = None,
    ) -> None:
        """Insert immutable event into meta.audit_trail."""
        q = f"""
            INSERT INTO `{self.catalog}`.`meta`.`audit_trail` (
                occurred_at, actor_user_id, actor_role, action, tenant_id, batch_id, reason, details_json
            )
            VALUES (
                current_timestamp(), :actor_user_id, :actor_role, :action, :tenant_id, :batch_id, :reason, :details_json
            )
        """
        try:
            self.cursor.execute(
                q,
                {
                    "actor_user_id": actor_user_id,
                    "actor_role": actor_role,
                    "action": action,
                    "tenant_id": tenant_id,
                    "batch_id": batch_id,
                    "reason": reason,
                    "details_json": details_json,
                },
            )
        except Exception as e:
            logger.warning("Failed to insert audit trail: %s", e)

    def reject_batch(self, batch_id: str, reason: str, user_id: int, tenant_id: int) -> None:
        """Mark batch as rejected, update pending uploads decision, and leave Bronze rows in place."""
        # Update pipeline_status
        q_status = f"""
            UPDATE {self.pipeline_table}
            SET status = 'rejected',
                stage = 'rejected',
                error_message = :reason,
                updated_at = current_timestamp()
            WHERE batch_id = :batch_id
        """
        self.cursor.execute(q_status, {"batch_id": batch_id, "reason": reason})

        # Update pending_uploads
        q_upload = f"""
            UPDATE {self.pending_table}
            SET status = 'rejected',
                decision = 'rejected',
                decision_reason = :reason,
                decided_by = :user_id,
                decided_at = current_timestamp()
            WHERE upload_id IN (
                SELECT upload_id FROM {self.pipeline_table} WHERE batch_id = :batch_id AND upload_id IS NOT NULL
            )
        """
        try:
            self.cursor.execute(q_upload, {"batch_id": batch_id, "reason": reason, "user_id": user_id})
        except Exception as e:
            logger.warning("Failed to update pending_uploads on reject: %s", e)

    def get_completeness_metrics(
        self,
        batch_id: str,
        template_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate total Bronze rows, accepted rows in Silver clean tables,
        rejected rows logged in meta.data_quality_log, and completeness percentage.
        Computed on-demand from existing bronze/silver/meta.data_quality_log tables.
        """
        # 1. Total rows ingested into Bronze
        orders_bronze_q = f"SELECT count(*) FROM {self.raw_orders_table} WHERE batch_id = :batch_id"
        self.cursor.execute(orders_bronze_q, {"batch_id": batch_id})
        orders_bronze_res = self.cursor.fetchone()
        orders_bronze_count = int(orders_bronze_res[0]) if orders_bronze_res and orders_bronze_res[0] is not None else 0

        shipping_bronze_q = f"SELECT count(*) FROM {self.raw_shipping_table} WHERE batch_id = :batch_id"
        self.cursor.execute(shipping_bronze_q, {"batch_id": batch_id})
        shipping_bronze_res = self.cursor.fetchone()
        shipping_bronze_count = int(shipping_bronze_res[0]) if shipping_bronze_res and shipping_bronze_res[0] is not None else 0

        bronze_count = orders_bronze_count + shipping_bronze_count

        # 2. Rows successfully written to Silver clean tables
        orders_silver_q = f"SELECT count(*) FROM {self.clean_orders_table} WHERE batch_id = :batch_id"
        self.cursor.execute(orders_silver_q, {"batch_id": batch_id})
        orders_silver_res = self.cursor.fetchone()
        orders_silver_count = int(orders_silver_res[0]) if orders_silver_res and orders_silver_res[0] is not None else 0

        shipping_silver_q = f"SELECT count(*) FROM {self.clean_shipping_table} WHERE batch_id = :batch_id"
        self.cursor.execute(shipping_silver_q, {"batch_id": batch_id})
        shipping_silver_res = self.cursor.fetchone()
        shipping_silver_count = int(shipping_silver_res[0]) if shipping_silver_res and shipping_silver_res[0] is not None else 0

        accepted_rows = orders_silver_count + shipping_silver_count

        # 3. Rejected rows logged in meta.data_quality_log
        rejections_q = f"SELECT count(*) FROM {self.dq_log_table} WHERE batch_id = :batch_id"
        self.cursor.execute(rejections_q, {"batch_id": batch_id})
        rejections_res = self.cursor.fetchone()
        rejected_rows = int(rejections_res[0]) if rejections_res and rejections_res[0] is not None else 0

        # Determine total rows: bronze_count with fallback to accepted + rejected if bronze was truncated
        total_rows = bronze_count
        if total_rows == 0 and (accepted_rows + rejected_rows) > 0:
            total_rows = accepted_rows + rejected_rows

        completeness_percentage = (
            round((accepted_rows / total_rows) * 100.0, 2) if total_rows > 0 else 0.0
        )

        return {
            "total_rows": total_rows,
            "accepted_rows": accepted_rows,
            "rejected_rows": rejected_rows,
            "completeness_percentage": completeness_percentage,
        }
