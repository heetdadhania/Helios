#!/usr/bin/env python3
"""
Helios Data Platform - Reset Runtime Data Script
Cleans all transactional and runtime operational data while strictly preserving
tenants, users, team assignments, API keys, database connections, and static dimensions.

Usage:
    python scripts/maintenance/reset_runtime_data.py [--confirm]
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.stdout.reconfigure(line_buffering=True)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.db.base import databricks_cursor

# Tables to reset (all rows deleted)
RESET_TABLES: List[str] = [
    "platform.pending_uploads",
    "platform.pipeline_status",
    "platform.inferred_schema",
    "platform.notification_log",
    "platform.support_messages",
    "meta.etl_audit_log",
    "meta.data_quality_log",
    "meta.audit_trail",
    "bronze.raw_orders",
    "bronze.raw_shipping",
    "silver.orders_clean",
    "silver.shipping_clean",
    "gold.fact_orders",
    "gold.fact_shipments",
    "gold.fact_orders_daily_summary",
    "gold.dim_product",
    "gold.dim_customer",
]

# Tables to keep (rows preserved and counted)
KEEP_TABLES: List[str] = [
    "platform.tenants",
    "platform.users",
    "platform.team_assignments",
    "platform.api_keys",
    "platform.db_connections",
    "gold.dim_date",
    "gold.dim_shipping_mode",
    "gold.dim_delivery_status",
]

CATALOG = "helios_catalog"


def get_table_counts(cur, tables: List[str]) -> Dict[str, int]:
    """Retrieve row counts for specified tables."""
    counts: Dict[str, int] = {}
    for tbl in tables:
        full_table = f"`{CATALOG}`.{tbl}"
        try:
            cur.execute(f"SELECT count(*) FROM {full_table}")
            counts[tbl] = cur.fetchone()[0]
        except Exception as exc:
            counts[tbl] = f"Error: {exc}"  # type: ignore
    return counts


def print_counts_table(title: str, counts: Dict[str, int]) -> None:
    """Print formatted summary table of row counts."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")
    print(f"{'Table':<42} | {'Row Count':>12}")
    print(f"{'-' * 42}-+-{'-' * 12}")
    for tbl, cnt in counts.items():
        print(f"{tbl:<42} | {str(cnt):>12}")
    print(f"{'=' * 60}\n")


def collect_volume_files(cur) -> List[str]:
    """Retrieve file paths recorded in platform.pending_uploads."""
    try:
        cur.execute(f"SELECT file_path FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE file_path IS NOT NULL")
        return [row[0] for row in cur.fetchall() if row[0]]
    except Exception as exc:
        print(f"Warning: Could not fetch pending_uploads file paths: {exc}")
        return []


def delete_volume_files(file_paths: List[str]) -> None:
    """List and delete Volume files from disk."""
    print(f"\n--- Volume Uploads Cleanup ({len(file_paths)} files recorded in DB) ---")
    deleted_count = 0
    not_found_count = 0

    # Also inspect local volume root directory
    volume_roots = [
        Path(r"C:\Volumes\helios\bronze\uploads"),
        Path(r"\Volumes\helios\bronze\uploads"),
        REPO_ROOT / "storage" / "volumes" / "helios" / "bronze" / "uploads",
    ]

    seen_files = set()
    for fp in file_paths:
        p_candidates = [
            Path(fp),
            Path(r"C:" + fp) if fp.startswith("/") or fp.startswith("\\") else None,
        ]
        found = False
        for cand in p_candidates:
            if cand and cand.is_file():
                seen_files.add(cand.resolve())
                print(f"  Found DB-referenced file: {cand}")
                try:
                    cand.unlink()
                    deleted_count += 1
                    found = True
                    break
                except Exception as del_err:
                    print(f"    Failed to delete {cand}: {del_err}")

        if not found:
            not_found_count += 1

    # Also clean any leftover files in the volume root directories
    for root in volume_roots:
        if root.exists():
            for p in list(root.rglob("*")):
                if p.is_file() and p.resolve() not in seen_files:
                    print(f"  Found unreferenced volume file: {p}")
                    try:
                        p.unlink()
                        deleted_count += 1
                    except Exception as err:
                        print(f"    Failed to delete {p}: {err}")

            # Clean empty directories
            for d in sorted(list(root.rglob("*")), key=lambda p: len(str(p)), reverse=True):
                if d.is_dir() and not any(d.iterdir()):
                    try:
                        d.rmdir()
                    except Exception:
                        pass

    print(f"Volume files deleted: {deleted_count}, Already absent on disk: {not_found_count}")


def cleanup_verification_credentials(cur) -> Tuple[int, int, int]:
    """
    Deactivates verification database connections and API keys, and deletes
    ephemeral verification credentials from Databricks Secrets.
    Strictly preserves seed connections and seed API keys.
    Returns: (deactivated_db_conns, deleted_secrets, deactivated_api_keys)
    """
    try:
        from app.core.secrets_manager import get_databricks_workspace_client
        ws = get_databricks_workspace_client()
    except Exception as exc:
        print(f"Warning: Could not initialize Databricks WorkspaceClient: {exc}")
        ws = None

    deleted_secrets_count = 0
    deactivated_conns_count = 0
    deactivated_keys_count = 0

    # 1. Verification DB Connections: connection_id != 1 (seed connection is connection_id 1)
    try:
        cur.execute(
            f"SELECT connection_id, encrypted_credential_ref, is_active FROM `{CATALOG}`.`platform`.`db_connections` "
            "WHERE connection_id != 1"
        )
        verif_conns = cur.fetchall()
        for row in verif_conns:
            cid = row[0]
            cred_ref = row[1]
            is_active = row[2]

            # Delete credential from Databricks Secrets if present
            if ws and cred_ref and ":" in cred_ref:
                scope, key = cred_ref.split(":", 1)
                try:
                    ws.secrets.delete_secret(scope=scope, key=key)
                    print(f"  [Secrets Cleanup] Deleted Databricks secret {scope}:{key}")
                    deleted_secrets_count += 1
                except Exception:
                    pass

            if is_active:
                cur.execute(
                    f"UPDATE `{CATALOG}`.`platform`.`db_connections` SET is_active = false WHERE connection_id = :cid",
                    {"cid": cid},
                )
                deactivated_conns_count += 1
    except Exception as exc:
        print(f"Warning during DB connections verification cleanup: {exc}")

    # 2. Verification API Keys: api_key_id NOT IN (1, 2, 3, 4) (seed keys are 1, 2, 3, 4)
    try:
        cur.execute(
            f"SELECT api_key_id, is_active FROM `{CATALOG}`.`platform`.`api_keys` "
            "WHERE api_key_id NOT IN (1, 2, 3, 4)"
        )
        verif_keys = cur.fetchall()
        for row in verif_keys:
            kid = row[0]
            is_active = row[1]
            if is_active:
                cur.execute(
                    f"UPDATE `{CATALOG}`.`platform`.`api_keys` SET is_active = false WHERE api_key_id = :kid",
                    {"kid": kid},
                )
                deactivated_keys_count += 1
    except Exception as exc:
        print(f"Warning during API keys verification cleanup: {exc}")

    return deactivated_conns_count, deleted_secrets_count, deactivated_keys_count


def get_credentials_counts(cur) -> Dict[str, Dict[str, int]]:
    """Retrieve total and active counts for db_connections and api_keys."""
    cur.execute(f"SELECT count(*), sum(case when is_active then 1 else 0 end) FROM `{CATALOG}`.`platform`.`db_connections`")
    db_row = cur.fetchone() or (0, 0)
    
    cur.execute(f"SELECT count(*), sum(case when is_active then 1 else 0 end) FROM `{CATALOG}`.`platform`.`api_keys`")
    api_row = cur.fetchone() or (0, 0)
    
    return {
        "platform.db_connections": {"total": db_row[0] or 0, "active": db_row[1] or 0},
        "platform.api_keys": {"total": api_row[0] or 0, "active": api_row[1] or 0},
    }


def main():
    parser = argparse.ArgumentParser(description="Reset Helios runtime data while keeping static and config tables.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicit confirmation flag required to execute data reset.",
    )
    args = parser.parse_args()

    with databricks_cursor() as cur:
        # 1. Row counts BEFORE
        print("\n[STEP 1] Fetching pre-reset row counts...")
        reset_counts_before = get_table_counts(cur, RESET_TABLES)
        keep_counts_before = get_table_counts(cur, KEEP_TABLES)
        cred_counts_before = get_credentials_counts(cur)

        print_counts_table("PRE-RESET COUNTS (Tables to be emptied)", reset_counts_before)
        print_counts_table("PRE-RESET COUNTS (Tables to be PRESERVED)", keep_counts_before)
        print("Pre-Reset Credentials Status:")
        for tbl, stat in cred_counts_before.items():
            print(f"  {tbl:<28}: Total={stat['total']}, Active={stat['active']}, Inactive={stat['total'] - stat['active']}")

        # 2. Check --confirm flag
        if not args.confirm:
            print("=" * 60)
            print("DRY RUN COMPLETE.")
            print("Refusing to delete runtime data because '--confirm' was not passed.")
            print("To execute full runtime reset, run with: --confirm")
            print("=" * 60)
            sys.exit(0)

        # 3. Collect volume files to delete
        print("\n[STEP 2] Collecting volume upload files for deletion...")
        file_paths = collect_volume_files(cur)
        print(f"Found {len(file_paths)} file paths recorded in platform.pending_uploads.")
        for fp in file_paths[:10]:
            print(f"  {fp}")
        if len(file_paths) > 10:
            print(f"  ... and {len(file_paths) - 10} more.")

        # 4. Execute SQL deletions
        sql_file = Path(__file__).resolve().parent / "reset_runtime_data.sql"
        print(f"\n[STEP 3] Executing deletion SQL from {sql_file.name}...")
        with open(sql_file, "r", encoding="utf-8") as f:
            raw_sql = f.read()

        # Remove comments line-by-line first
        lines = []
        for line in raw_sql.splitlines():
            clean_l = line.strip()
            if clean_l.startswith("--"):
                continue
            lines.append(line)
        cleaned_sql = "\n".join(lines)

        statements = [stmt.strip() for stmt in cleaned_sql.split(";") if stmt.strip()]
        for stmt in statements:
            print(f"Executing: {stmt}")
            cur.execute(stmt)

        print("All runtime tables successfully truncated/deleted.")

        # 5. Delete physical files from volume
        print("\n[STEP 4] Deleting physical files from volume uploads folder...")
        delete_volume_files(file_paths)

        # 6. Cleanup verification database connections, secrets, and API keys
        print("\n[STEP 4b] Cleaning up verification credentials & Databricks secrets...")
        deact_conns, del_secrets, deact_keys = cleanup_verification_credentials(cur)
        print(f"  Deactivated verification DB connections: {deact_conns}")
        print(f"  Deleted verification Databricks secrets: {del_secrets}")
        print(f"  Deactivated verification API keys: {deact_keys}")

        # 7. Row counts AFTER
        print("\n[STEP 5] Fetching post-reset row counts...")
        reset_counts_after = get_table_counts(cur, RESET_TABLES)
        keep_counts_after = get_table_counts(cur, KEEP_TABLES)
        cred_counts_after = get_credentials_counts(cur)

        print_counts_table("POST-RESET COUNTS (Tables emptied)", reset_counts_after)
        print_counts_table("POST-RESET COUNTS (Tables PRESERVED)", keep_counts_after)
        print("Post-Reset Credentials Status:")
        for tbl, stat in cred_counts_after.items():
            print(f"  {tbl:<28}: Total={stat['total']}, Active={stat['active']} (Seed preserved), Inactive={stat['total'] - stat['active']} (Verification deactivated)")

        # Verify all reset tables are 0
        non_zero = {t: c for t, c in reset_counts_after.items() if c != 0}
        if non_zero:
            print(f"WARNING: Some reset tables still have rows: {non_zero}")
            sys.exit(1)
        else:
            print("VERIFICATION SUCCESS: All runtime tables are at exactly 0 rows.")
            print("Configuration and dimension tables remain intact.")


if __name__ == "__main__":
    main()
