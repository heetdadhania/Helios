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

tables_to_check = [
    f"{CATALOG}.platform.users",
    f"{CATALOG}.platform.pending_uploads",
    f"{CATALOG}.platform.pipeline_status",
    f"{CATALOG}.platform.notification_log",
    f"{CATALOG}.meta.etl_audit_log",
    f"{CATALOG}.meta.audit_trail",
]

print(f"Connecting to Databricks Catalog: {CATALOG}")

with databricks_cursor() as cur:
    for table in tables_to_check:
        print("\n" + "=" * 80)
        print(f"TABLE: {table}")
        print("=" * 80)
        try:
            cur.execute(f"DESCRIBE TABLE {table}")
            rows = cur.fetchall()
            for r in rows:
                col_name = r[0]
                data_type = r[1]
                comment = r[2] if len(r) > 2 else ""
                print(f"  {col_name:30} {data_type:20} {comment}")
        except Exception as e:
            print(f"  ERROR / NOT FOUND: {e}")

    # Also check if pipeline_status has any constraints
    print("\n" + "=" * 80)
    print(f"CONSTRAINTS / EXTENDED: {CATALOG}.platform.pipeline_status")
    print("=" * 80)
    try:
        cur.execute(f"DESCRIBE EXTENDED {CATALOG}.platform.pipeline_status")
        rows = cur.fetchall()
        for r in rows:
            print(f"  {r[0]:30} {r[1] if len(r) > 1 else ''}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Check distinct status values in pipeline_status, pending_uploads, notification_log
    for t, col in [
        (f"{CATALOG}.platform.pipeline_status", "status"),
        (f"{CATALOG}.platform.pending_uploads", "status"),
        (f"{CATALOG}.platform.notification_log", "status"),
    ]:
        print(f"\nDistinct values of {t}.{col}:")
        try:
            cur.execute(f"SELECT DISTINCT {col} FROM {t}")
            vals = cur.fetchall()
            print(f"  {[v[0] for v in vals]}")
        except Exception as e:
            print(f"  ERROR: {e}")
