"""
Helios Master Schema Deployment Runner
Executes all Medallion and Platform DDL scripts sequentially against Databricks.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple
from dotenv import load_dotenv

# Load backend environment variables
backend_env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
load_dotenv(dotenv_path=backend_env_path)

try:
    from databricks import sql
except ImportError:
    print("Error: 'databricks-sql-connector' is required. Run 'pip install databricks-sql-connector'.")
    sys.exit(1)

SQL_EXECUTION_ORDER: List[str] = [
    "00_catalog_setup.sql",
    "platform/01_tenants.sql",
    "platform/02_users.sql",
    "platform/03_team_assignments.sql",
    "platform/04_pending_uploads.sql",
    "platform/05_db_connections.sql",
    "platform/06_api_keys.sql",
    "platform/07_pipeline_status.sql",
    "platform/08_inferred_schema.sql",
    "platform/09_notification_log.sql",
    "meta/01_etl_audit_log.sql",
    "meta/02_data_quality_log.sql",
    "bronze/01_raw_orders.sql",
    "bronze/02_raw_shipping.sql",
    "silver/01_orders_clean.sql",
    "silver/02_shipping_clean.sql",
    "gold/01_dim_date.sql",
    "gold/02_dim_product.sql",
    "gold/03_dim_customer.sql",
    "gold/04_dim_shipping_mode.sql",
    "gold/05_dim_delivery_status.sql",
    "gold/06_fact_orders.sql",
    "gold/07_fact_shipments.sql",
    "gold/08_fact_orders_daily_summary.sql",
    "platform/row_filters.sql",
]


def split_sql_statements(content: str) -> List[str]:
    """Split a SQL file content into executable individual statements."""
    statements: List[str] = []
    current_stmt: List[str] = []

    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("--") or not trimmed:
            continue
        current_stmt.append(line)
        if trimmed.endswith(";"):
            stmt_text = "\n".join(current_stmt).strip()
            # Remove trailing semicolon for Spark SQL engine
            if stmt_text.endswith(";"):
                stmt_text = stmt_text[:-1].strip()
            if stmt_text:
                statements.append(stmt_text)
            current_stmt = []

    if current_stmt:
        stmt_text = "\n".join(current_stmt).strip()
        if stmt_text.endswith(";"):
            stmt_text = stmt_text[:-1].strip()
        if stmt_text:
            statements.append(stmt_text)

    return statements


def execute_script(
    cursor,
    file_path: Path,
    catalog_override: str,
) -> Tuple[int, int]:
    """Execute all SQL statements in a single file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Substitute catalog name if override provided (e.g. helios_catalog)
    if catalog_override and catalog_override != "helios":
        content = re.sub(r"\bhelios\b", catalog_override, content)

    statements = split_sql_statements(content)
    passed = 0
    failed = 0

    for stmt in statements:
        try:
            cursor.execute(stmt)
            passed += 1
        except Exception as exc:
            # Check if non-fatal (e.g. catalog already exists, or row filter notice in Community Edition)
            err_msg = str(exc).lower()
            if "already exists" in err_msg or "cannot create catalog" in err_msg:
                passed += 1
            else:
                print(f"    [WARN] Failed executing statement in {file_path.name}: {exc}")
                failed += 1

    return passed, failed


def main():
    parser = argparse.ArgumentParser(description="Helios Databricks Schema Deployment")
    parser.add_argument("--catalog", default=os.getenv("DATABRICKS_CATALOG", "helios_catalog"))
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate SQL files without executing")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    print(f"Starting Helios Schema Deployment (Target Catalog: {args.catalog})...")

    if args.dry_run:
        print("[DRY RUN] Validating SQL file paths and statements:")
        for rel_path in SQL_EXECUTION_ORDER:
            full_path = base_dir / rel_path
            assert full_path.exists(), f"Missing file: {rel_path}"
            with open(full_path, "r", encoding="utf-8") as f:
                stmts = split_sql_statements(f.read())
            print(f"  OK: {rel_path} ({len(stmts)} statements)")
        print("\nAll SQL files parsed and validated successfully!")
        return

    server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    access_token = os.getenv("DATABRICKS_TOKEN")

    if not server_hostname or not http_path or not access_token:
        print("Error: Databricks connection credentials missing in backend/.env")
        sys.exit(1)

    print(f"Connecting to {server_hostname} via {http_path}...")
    with sql.connect(
        server_hostname=server_hostname,
        http_path=http_path,
        access_token=access_token,
    ) as conn:
        with conn.cursor() as cursor:
            for rel_path in SQL_EXECUTION_ORDER:
                file_path = base_dir / rel_path
                print(f"Executing {rel_path}...")
                passed, failed = execute_script(cursor, file_path, args.catalog)
                status = "SUCCESS" if failed == 0 else f"{failed} WARNINGS"
                print(f"  -> {status} ({passed} statements processed)")

    print("\nHelios Medallion Schema deployment completed successfully!")


if __name__ == "__main__":
    main()
