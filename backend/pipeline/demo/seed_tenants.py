#!/usr/bin/env python3
"""
Helios Data Platform - Demo Tenant & Credentials Seeding Script

Idempotently provisions demo organizations, user accounts across all 3 roles
(admin, team_member, smb_owner), team assignments, a demo database connection (Module 4),
and a demo API key (Module 5) to enable testing all 3 ingestion channels.

Usage:
    python pipeline/demo/seed_tenants.py [--dry-run] [--catalog helios]
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add backend directory to sys.path to leverage core security & DB utilities
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("helios.demo.seed_tenants")

try:
    from app.core.api_key_security import hash_api_key, mask_api_key
    from app.core.config import settings
    from app.core.security import get_password_hash
    from app.db.base import get_databricks_connection
except ImportError as exc:
    logger.error("Failed to import backend core packages: %s", exc)
    raise

# Demo Password shared across all demo accounts for straightforward onboarding
DEMO_PASSWORD_PLAIN = "HeliosDemo2026!"
DEMO_API_KEY_PLAIN = "helios_live_vanguard_demo_api_key_2026"

DEMO_TENANTS: List[Dict[str, Any]] = [
    {
        "tenant_id": 1,
        "business_name": "Apex Consumer Goods",
        "industry": "Apparel & Footwear",
        "contact_email": "owner@apexconsumer.com",
    },
    {
        "tenant_id": 2,
        "business_name": "Pacific Tech & Corporate",
        "industry": "Consumer Electronics",
        "contact_email": "owner@pacifictech.com",
    },
    {
        "tenant_id": 3,
        "business_name": "Vanguard Home Office",
        "industry": "Office Supplies & Furniture",
        "contact_email": "owner@vanguardhome.com",
    },
]

DEMO_USERS: List[Dict[str, Any]] = [
    {
        "name": "Helios Admin",
        "email": "admin@helios.io",
        "role": "admin",
        "tenant_id": None,
    },
    {
        "name": "Sarah Jenkins",
        "email": "team@helios.io",
        "role": "team_member",
        "tenant_id": None,
    },
    {
        "name": "Marcus Vance",
        "email": "owner@apexconsumer.com",
        "role": "smb_owner",
        "tenant_id": 1,
    },
    {
        "name": "Elena Rostova",
        "email": "owner@pacifictech.com",
        "role": "smb_owner",
        "tenant_id": 2,
    },
    {
        "name": "David Kim",
        "email": "owner@vanguardhome.com",
        "role": "smb_owner",
        "tenant_id": 3,
    },
]

DEMO_DB_CONNECTION: Dict[str, Any] = {
    "tenant_id": 2,
    "db_type": "postgresql",
    "host": "demo-pg.helios.internal",
    "port": 5432,
    "database_name": "pacific_ecom_prod",
    "username": "helios_sync_user",
    "encrypted_credential_ref": "helios_tenant_2:helios-tenant-2-conn-demo1",
    "table_or_query": "SELECT * FROM daily_transactions WHERE status = 'COMPLETED'",
    "is_active": True,
}


def build_seed_sql_statements(catalog: str = "helios") -> List[str]:
    """Generate SQL statements required to seed demo tenants, users, and credentials."""
    password_hash = get_password_hash(DEMO_PASSWORD_PLAIN)
    api_key_hash = hash_api_key(DEMO_API_KEY_PLAIN)
    api_key_prefix = mask_api_key(DEMO_API_KEY_PLAIN)

    statements: List[str] = [
        f"USE CATALOG {catalog};",
        "USE SCHEMA platform;",
    ]

    # Seed Tenants (omit tenant_id as it is GENERATED ALWAYS AS IDENTITY)
    for t in DEMO_TENANTS:
        stmt = f"""
MERGE INTO {catalog}.platform.tenants AS target
USING (
  SELECT 
    '{t['business_name']}' AS business_name,
    '{t['industry']}' AS industry,
    '{t['contact_email']}' AS contact_email,
    true AS is_active
) AS source
ON target.contact_email = source.contact_email
WHEN MATCHED THEN
  UPDATE SET 
    business_name = source.business_name,
    industry = source.industry,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (business_name, industry, contact_email, is_active)
  VALUES (source.business_name, source.industry, source.contact_email, source.is_active);
""".strip()
        statements.append(stmt)

    # Seed Users (dynamically resolve tenant_id from platform.tenants for SMB owners)
    for u in DEMO_USERS:
        if u["role"] == "smb_owner":
            tenant_join = f"INNER JOIN {catalog}.platform.tenants t ON t.contact_email = '{u['email']}'"
            tenant_select = "t.tenant_id"
        else:
            tenant_join = ""
            tenant_select = "CAST(NULL AS BIGINT) AS tenant_id"

        stmt = f"""
MERGE INTO {catalog}.platform.users AS target
USING (
  SELECT 
    '{u['email']}' AS email,
    '{u['name']}' AS name,
    '{password_hash}' AS password_hash,
    '{u['role']}' AS role,
    {tenant_select},
    true AS is_active
  FROM (SELECT 1) _dummy
  {tenant_join}
) AS source
ON target.email = source.email
WHEN MATCHED THEN
  UPDATE SET 
    name = source.name,
    password_hash = source.password_hash,
    role = source.role,
    tenant_id = source.tenant_id,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (name, email, password_hash, role, tenant_id, is_active)
  VALUES (source.name, source.email, source.password_hash, source.role, source.tenant_id, source.is_active);
""".strip()
        statements.append(stmt)

    # Seed Team Assignments (Sarah Jenkins assigned to Tenants 1 & 2)
    team_assignment_stmt = f"""
MERGE INTO {catalog}.platform.team_assignments AS target
USING (
  SELECT u.user_id, t.tenant_id
  FROM {catalog}.platform.users u
  CROSS JOIN (
    SELECT tenant_id FROM {catalog}.platform.tenants 
    WHERE contact_email IN ('owner@apexconsumer.com', 'owner@pacifictech.com')
  ) t
  WHERE u.email = 'team@helios.io'
) AS source
ON target.user_id = source.user_id AND target.tenant_id = source.tenant_id
WHEN NOT MATCHED THEN
  INSERT (user_id, tenant_id)
  VALUES (source.user_id, source.tenant_id);
""".strip()
    statements.append(team_assignment_stmt)

    # Seed Demo DB Connection for Tenant 2 (Module 4)
    escaped_query = DEMO_DB_CONNECTION['table_or_query'].replace("'", "''")
    db_stmt = f"""
MERGE INTO {catalog}.platform.db_connections AS target
USING (
  SELECT 
    t.tenant_id,
    '{DEMO_DB_CONNECTION['db_type']}' AS db_type,
    '{DEMO_DB_CONNECTION['host']}' AS host,
    {DEMO_DB_CONNECTION['port']} AS port,
    '{DEMO_DB_CONNECTION['database_name']}' AS database_name,
    '{DEMO_DB_CONNECTION['username']}' AS username,
    '{DEMO_DB_CONNECTION['encrypted_credential_ref']}' AS encrypted_credential_ref,
    '{escaped_query}' AS table_or_query,
    true AS is_active
  FROM {catalog}.platform.tenants t
  WHERE t.contact_email = 'owner@pacifictech.com'
) AS source
ON target.tenant_id = source.tenant_id AND target.encrypted_credential_ref = source.encrypted_credential_ref
WHEN MATCHED THEN
  UPDATE SET 
    db_type = source.db_type,
    host = source.host,
    port = source.port,
    database_name = source.database_name,
    username = source.username,
    table_or_query = source.table_or_query,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (tenant_id, db_type, host, port, database_name, username, encrypted_credential_ref, table_or_query, is_active)
  VALUES (source.tenant_id, source.db_type, source.host, source.port, source.database_name, source.username, source.encrypted_credential_ref, source.table_or_query, source.is_active);
""".strip()
    statements.append(db_stmt)

    # Seed Demo API Key for Tenant 3 (Module 5)
    api_key_stmt = f"""
MERGE INTO {catalog}.platform.api_keys AS target
USING (
  SELECT 
    t.tenant_id,
    '{api_key_hash}' AS key_hash,
    '{api_key_prefix}' AS key_prefix,
    true AS is_active
  FROM {catalog}.platform.tenants t
  WHERE t.contact_email = 'owner@vanguardhome.com'
) AS source
ON target.tenant_id = source.tenant_id AND target.key_prefix = source.key_prefix
WHEN MATCHED THEN
  UPDATE SET 
    key_hash = source.key_hash,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (tenant_id, key_hash, key_prefix, is_active)
  VALUES (source.tenant_id, source.key_hash, source.key_prefix, source.is_active);
""".strip()
    statements.append(api_key_stmt)

    return statements


def execute_seed_against_databricks(statements: List[str], catalog: str) -> bool:
    """Execute SQL statements against live Databricks SQL endpoint."""
    try:
        conn = get_databricks_connection(catalog=catalog, schema="platform")
        cursor = conn.cursor()
        for idx, sql_stmt in enumerate(statements, 1):
            logger.info("Executing statement %d/%d...", idx, len(statements))
            cursor.execute(sql_stmt)
        cursor.close()
        conn.close()
        logger.info("Successfully executed all seed statements against Databricks!")
        return True
    except Exception as exc:
        logger.warning(
            "Could not connect or execute against Databricks endpoint (%s). "
            "Outputting SQL script for manual or offline execution.",
            exc,
        )
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Helios Platform Demo Tenants & Credentials")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL statements without connecting or modifying Databricks",
    )
    parser.add_argument(
        "--catalog",
        type=str,
        default=getattr(settings, "DATABRICKS_CATALOG", "helios"),
        help="Target Databricks Unity Catalog name (default: helios)",
    )
    parser.add_argument(
        "--sql-output",
        type=str,
        default=None,
        help="Optional file path to write generated SQL script to",
    )

    args = parser.parse_args()
    logger.info("Preparing demo seed statements for catalog: %s", args.catalog)

    statements = build_seed_sql_statements(catalog=args.catalog)

    if args.sql_output:
        out_file = Path(args.sql_output)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n\n".join(statements) + "\n")
        logger.info("Wrote SQL seed script to: %s", out_file)

    if args.dry_run:
        logger.info("=== DRY RUN MODE: Generated SQL Statements ===")
        for stmt in statements:
            print(stmt + "\n")
    else:
        logger.info("Attempting to seed Databricks SQL endpoint...")
        success = execute_seed_against_databricks(statements, catalog=args.catalog)
        if not success:
            logger.info("Printing statements for copy-paste into Databricks SQL Editor:")
            for stmt in statements:
                print(stmt + "\n")

    logger.info("Demo seeding script complete!")
    logger.info("Demo password: %s", DEMO_PASSWORD_PLAIN)
    logger.info("Demo API key (Tenant 3): %s", DEMO_API_KEY_PLAIN)


if __name__ == "__main__":
    main()
