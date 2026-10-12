#!/usr/bin/env python3
"""
Applies schema migrations for Helios Platform & Meta layers safely and idempotently.
Adds:
1. platform.users: last_login_at TIMESTAMP, failed_login_count INT default 0, locked_until TIMESTAMP, password_changed_at TIMESTAMP
2. platform.pending_uploads: file_hash STRING, decision STRING, decision_reason STRING, decided_by BIGINT, decided_at TIMESTAMP
3. platform.pipeline_status: last_heartbeat_at TIMESTAMP, failed_stage STRING, failure_message STRING, failure_next_step STRING,
   cancel_requested BOOLEAN default false, cancelled_by BIGINT, started_at TIMESTAMP, finished_at TIMESTAMP,
   allow status values ingesting, pending_review, running, success, failed, rejected, cancelled, stalled
4. meta.audit_trail: audit_id BIGINT identity, occurred_at TIMESTAMP, actor_user_id BIGINT, actor_role STRING,
   action STRING, tenant_id BIGINT, batch_id STRING, reason STRING, details_json STRING
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")

from app.db.base import databricks_cursor
from app.core.config import settings

CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")

def get_existing_columns(cur, schema: str, table: str) -> set:
    cur.execute(f"""
        SELECT column_name
        FROM {CATALOG}.information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{table}'
    """)
    return {row[0].lower() for row in cur.fetchall()}

def apply_migrations():
    print(f"Connecting to Databricks Catalog: {CATALOG}")
    with databricks_cursor() as cur:
        # -------------------------------------------------------------
        # 1. platform.users
        # -------------------------------------------------------------
        print("\n--- Applying Migrations to platform.users ---")
        cur.execute(f"ALTER TABLE {CATALOG}.platform.users SET TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')")
        user_cols = get_existing_columns(cur, "platform", "users")
        
        users_to_add = [
            ("last_login_at", "TIMESTAMP", "Timestamp of last successful user authentication", None),
            ("failed_login_count", "INT", "Count of consecutive failed login attempts", 0),
            ("locked_until", "TIMESTAMP", "Timestamp until which user account is locked due to repeated failed logins", None),
            ("password_changed_at", "TIMESTAMP", "Timestamp of most recent password modification", None),
        ]
        
        for col, col_type, comment, default_val in users_to_add:
            if col.lower() not in user_cols:
                print(f"  Adding column platform.users.{col} ({col_type})...")
                cur.execute(f"ALTER TABLE {CATALOG}.platform.users ADD COLUMNS ({col} {col_type} COMMENT '{comment}')")
                if default_val is not None:
                    cur.execute(f"ALTER TABLE {CATALOG}.platform.users ALTER COLUMN {col} SET DEFAULT {default_val}")
            else:
                print(f"  Column platform.users.{col} already exists (skipping)")
                
        # Backfill NULL failed_login_count for existing rows
        cur.execute(f"UPDATE {CATALOG}.platform.users SET failed_login_count = 0 WHERE failed_login_count IS NULL")
        print("  Backfilled failed_login_count default for existing users.")

        # -------------------------------------------------------------
        # 2. platform.pending_uploads
        # -------------------------------------------------------------
        print("\n--- Applying Migrations to platform.pending_uploads ---")
        uploads_cols = get_existing_columns(cur, "platform", "pending_uploads")
        
        uploads_to_add = [
            ("file_hash", "STRING", "Cryptographic hash (SHA-256) of uploaded raw file"),
            ("decision", "STRING", "Review decision: approved or rejected"),
            ("decision_reason", "STRING", "Explanation or reviewer justification for review decision"),
            ("decided_by", "BIGINT", "Foreign key to platform.users for reviewer who decided upload"),
            ("decided_at", "TIMESTAMP", "Timestamp when review decision was recorded"),
        ]
        
        for col, col_type, comment in uploads_to_add:
            if col.lower() not in uploads_cols:
                print(f"  Adding column platform.pending_uploads.{col} ({col_type})...")
                cur.execute(f"ALTER TABLE {CATALOG}.platform.pending_uploads ADD COLUMNS ({col} {col_type} COMMENT '{comment}')")
            else:
                print(f"  Column platform.pending_uploads.{col} already exists (skipping)")

        # -------------------------------------------------------------
        # 3. platform.pipeline_status
        # -------------------------------------------------------------
        print("\n--- Applying Migrations to platform.pipeline_status ---")
        cur.execute(f"ALTER TABLE {CATALOG}.platform.pipeline_status SET TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')")
        try:
            cur.execute(f"ALTER TABLE {CATALOG}.platform.pipeline_status DROP CONSTRAINT IF EXISTS chk_pipeline_status_status")
        except Exception:
            pass

        pipeline_cols = get_existing_columns(cur, "platform", "pipeline_status")
        
        pipeline_to_add = [
            ("last_heartbeat_at", "TIMESTAMP", "Timestamp of latest worker heartbeat during pipeline execution", None),
            ("failed_stage", "STRING", "Stage where pipeline execution failed", None),
            ("failure_message", "STRING", "Detailed error message or exception summary for pipeline failure", None),
            ("failure_next_step", "STRING", "Recommended remediation or next step for pipeline failure", None),
            ("cancel_requested", "BOOLEAN", "Flag indicating if operator requested cancellation", False),
            ("cancelled_by", "BIGINT", "Foreign key to platform.users who requested cancellation", None),
            ("started_at", "TIMESTAMP", "Execution start timestamp", None),
            ("finished_at", "TIMESTAMP", "Execution termination timestamp", None),
        ]
        
        for col, col_type, comment, default_val in pipeline_to_add:
            if col.lower() not in pipeline_cols:
                print(f"  Adding column platform.pipeline_status.{col} ({col_type})...")
                cur.execute(f"ALTER TABLE {CATALOG}.platform.pipeline_status ADD COLUMNS ({col} {col_type} COMMENT '{comment}')")
                if default_val is not None:
                    cur.execute(f"ALTER TABLE {CATALOG}.platform.pipeline_status ALTER COLUMN {col} SET DEFAULT {default_val}")
            else:
                print(f"  Column platform.pipeline_status.{col} already exists (skipping)")

        cur.execute(f"ALTER TABLE {CATALOG}.platform.pipeline_status ALTER COLUMN status COMMENT 'Processing state: ingesting, pending_review, running, success, failed, rejected, cancelled, stalled'")
        print("  Updated platform.pipeline_status.status comment with all 8 allowed lifecycle states.")

        # -------------------------------------------------------------
        # 4. meta.audit_trail
        # -------------------------------------------------------------
        print("\n--- Creating meta.audit_trail Table ---")
        create_audit_sql = f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.meta.audit_trail (
          audit_id BIGINT GENERATED ALWAYS AS IDENTITY,
          occurred_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Audit event occurrence timestamp',
          actor_user_id BIGINT COMMENT 'Foreign key to platform.users for actor triggering event',
          actor_role STRING COMMENT 'Role of actor: admin, team_member, smb_owner, system',
          action STRING NOT NULL COMMENT 'Audited action descriptor (e.g. upload_approved, upload_rejected, run_cancelled)',
          tenant_id BIGINT COMMENT 'Foreign key to platform.tenants associated with action',
          batch_id STRING COMMENT 'Optional pipeline execution batch UUID',
          reason STRING COMMENT 'User-provided justification or system reason for action',
          details_json STRING COMMENT 'JSON string containing event payload, metadata, or state diffs',
          CONSTRAINT pk_audit_trail PRIMARY KEY (audit_id)
        )
        USING DELTA
        TBLPROPERTIES (
          'delta.feature.allowColumnDefaults' = 'supported',
          'delta.autoOptimize.optimizeWrite' = 'true',
          'delta.autoOptimize.autoCompact' = 'true'
        )
        COMMENT 'Immutable audit trail capturing administrative, review, and pipeline operational actions'
        """
        cur.execute(create_audit_sql)
        print("  meta.audit_trail table verified / created successfully.")

def describe_all_tables():
    tables = [
        f"{CATALOG}.platform.users",
        f"{CATALOG}.platform.pending_uploads",
        f"{CATALOG}.platform.pipeline_status",
        f"{CATALOG}.meta.audit_trail",
    ]
    with databricks_cursor() as cur:
        for t in tables:
            print("\n" + "=" * 80)
            print(f"DESCRIBE TABLE: {t}")
            print("=" * 80)
            cur.execute(f"DESCRIBE TABLE {t}")
            for r in cur.fetchall():
                col = r[0]
                dtype = r[1]
                comment = r[2] if len(r) > 2 and r[2] is not None else ""
                print(f"  {col:30} {dtype:20} {comment}")

if __name__ == "__main__":
    apply_migrations()
    describe_all_tables()
