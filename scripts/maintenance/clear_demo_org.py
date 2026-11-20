"""
Faculty Demonstration Organization Cleanup Utility
=================================================
Cleans runtime data (Bronze, Silver, Gold, Batch, Quality Log, and Audit Log)
exclusively for the dedicated demonstration organization "Faculty Demo Traders".

STRICT SAFETY RESTRICTIONS:
- Refuses any organization ID other than "Faculty Demo Traders" (e.g. Tenants 1-10 are strictly protected).
- Requires explicit --confirm flag to execute.
- Prints exact counts of rows removed from each Medallion and Platform table.
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings
from app.db.base import databricks_cursor

DEMO_ORG_NAME = "Faculty Demo Traders"
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Clear runtime pipeline data for 'Faculty Demo Traders' to enable repeatable demonstrations."
    )
    parser.add_argument(
        "--tenant-id",
        type=int,
        required=False,
        default=None,
        help="Tenant ID of 'Faculty Demo Traders' (auto-detected if omitted).",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicit confirmation required to execute deletion.",
    )
    return parser.parse_args()


def get_demo_tenant_info(cursor, specified_tenant_id=None):
    if specified_tenant_id is not None:
        cursor.execute(
            f"SELECT tenant_id, business_name FROM `{CATALOG}`.`platform`.`tenants` WHERE tenant_id = :tid",
            {"tid": specified_tenant_id},
        )
        row = cursor.fetchone()
        if not row:
            print(f"[ERROR] Tenant ID {specified_tenant_id} does not exist in platform.tenants.")
            sys.exit(1)
        return row[0], row[1]

    cursor.execute(
        f"SELECT tenant_id, business_name FROM `{CATALOG}`.`platform`.`tenants` WHERE business_name = :name",
        {"name": DEMO_ORG_NAME},
    )
    row = cursor.fetchone()
    if not row:
        print(f"[ERROR] Organization '{DEMO_ORG_NAME}' does not exist in platform.tenants.")
        sys.exit(1)
    return row[0], row[1]


def main():
    args = parse_args()

    print("=" * 75)
    print("HELIOS DEMO CLEANUP UTILITY: Faculty Demo Traders")
    print("=" * 75)

    with databricks_cursor() as cursor:
        tenant_id, business_name = get_demo_tenant_info(cursor, args.tenant_id)

        # STRICT SAFETY GUARD: Refuse any tenant that is NOT "Faculty Demo Traders"
        if business_name.strip() != DEMO_ORG_NAME:
            print(
                f"\n[REFUSED] Target Tenant ID {tenant_id} is '{business_name}', NOT '{DEMO_ORG_NAME}'!"
            )
            print("Safety Violation: This script strictly refuses to touch any organization")
            print("other than the dedicated faculty demo tenant. Tenants 1 through 10 remain untouched.")
            sys.exit(1)

        # STRICT SAFETY GUARD: Require --confirm
        if not args.confirm:
            print("\n[REFUSED] Missing mandatory --confirm flag.")
            print(f"To clean runtime data for Tenant {tenant_id} ('{business_name}'), rerun with:")
            print(f"  python scripts/maintenance/clear_demo_org.py --tenant-id {tenant_id} --confirm")
            sys.exit(1)

        print(f"\nTarget Tenant Verified: ID {tenant_id} ('{business_name}')")
        print("Gathering associated batch IDs...")

        # Find all batch IDs belonging to this tenant
        cursor.execute(
            f"SELECT DISTINCT batch_id FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE tenant_id = :tid",
            {"tid": tenant_id},
        )
        batch_rows = cursor.fetchall()
        batch_ids = [r[0] for r in batch_rows if r[0]]
        print(f"Found {len(batch_ids)} pipeline batches associated with Tenant {tenant_id}.")

        deleted_summary = {}

        # 1. Gold Layer: fact_orders_daily_summary
        cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`gold`.`fact_orders_daily_summary` WHERE tenant_id = {tenant_id}")
        cnt_daily = cursor.fetchone()[0]
        if cnt_daily > 0:
            cursor.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_orders_daily_summary` WHERE tenant_id = {tenant_id}")
        deleted_summary["gold.fact_orders_daily_summary"] = cnt_daily

        # 2. Gold Layer: fact_shipments
        cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`gold`.`fact_shipments` WHERE tenant_id = {tenant_id}")
        cnt_shipments = cursor.fetchone()[0]
        if cnt_shipments > 0:
            cursor.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_shipments` WHERE tenant_id = {tenant_id}")
        deleted_summary["gold.fact_shipments"] = cnt_shipments

        # 3. Gold Layer: fact_orders
        cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE tenant_id = {tenant_id}")
        cnt_fact_orders = cursor.fetchone()[0]
        if cnt_fact_orders > 0:
            cursor.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_orders` WHERE tenant_id = {tenant_id}")
        deleted_summary["gold.fact_orders"] = cnt_fact_orders

        # 4. Silver Layer: shipping_clean
        cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`silver`.`shipping_clean` WHERE tenant_id = {tenant_id}")
        cnt_silver_shipping = cursor.fetchone()[0]
        if cnt_silver_shipping > 0:
            cursor.execute(f"DELETE FROM `{CATALOG}`.`silver`.`shipping_clean` WHERE tenant_id = {tenant_id}")
        deleted_summary["silver.shipping_clean"] = cnt_silver_shipping

        # 5. Silver Layer: orders_clean
        cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`silver`.`orders_clean` WHERE tenant_id = {tenant_id}")
        cnt_silver_orders = cursor.fetchone()[0]
        if cnt_silver_orders > 0:
            cursor.execute(f"DELETE FROM `{CATALOG}`.`silver`.`orders_clean` WHERE tenant_id = {tenant_id}")
        deleted_summary["silver.orders_clean"] = cnt_silver_orders

        # 6. Bronze Layer: raw_shipping
        cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`bronze`.`raw_shipping` WHERE tenant_id = {tenant_id}")
        cnt_bronze_shipping = cursor.fetchone()[0]
        if cnt_bronze_shipping > 0:
            cursor.execute(f"DELETE FROM `{CATALOG}`.`bronze`.`raw_shipping` WHERE tenant_id = {tenant_id}")
        deleted_summary["bronze.raw_shipping"] = cnt_bronze_shipping

        # 7. Bronze Layer: raw_orders
        cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE tenant_id = {tenant_id}")
        cnt_bronze_orders = cursor.fetchone()[0]
        if cnt_bronze_orders > 0:
            cursor.execute(f"DELETE FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE tenant_id = {tenant_id}")
        deleted_summary["bronze.raw_orders"] = cnt_bronze_orders

        # 8. Meta Layer: data_quality_log
        cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE tenant_id = {tenant_id}")
        cnt_dq = cursor.fetchone()[0]
        if cnt_dq > 0:
            cursor.execute(f"DELETE FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE tenant_id = {tenant_id}")
        deleted_summary["meta.data_quality_log"] = cnt_dq

        # 9. Meta Layer: etl_audit_log (by batch_id)
        cnt_audit = 0
        if batch_ids:
            batch_list_sql = ", ".join(f"'{b}'" for b in batch_ids)
            cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`meta`.`etl_audit_log` WHERE batch_id IN ({batch_list_sql})")
            cnt_audit = cursor.fetchone()[0]
            if cnt_audit > 0:
                cursor.execute(f"DELETE FROM `{CATALOG}`.`meta`.`etl_audit_log` WHERE batch_id IN ({batch_list_sql})")
        deleted_summary["meta.etl_audit_log"] = cnt_audit

        # 10. Platform: inferred_schema (by batch_id)
        cnt_schema = 0
        if batch_ids:
            batch_list_sql = ", ".join(f"'{b}'" for b in batch_ids)
            cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`platform`.`inferred_schema` WHERE batch_id IN ({batch_list_sql})")
            cnt_schema = cursor.fetchone()[0]
            if cnt_schema > 0:
                cursor.execute(f"DELETE FROM `{CATALOG}`.`platform`.`inferred_schema` WHERE batch_id IN ({batch_list_sql})")
        deleted_summary["platform.inferred_schema"] = cnt_schema

        # 11. Platform: pending_uploads
        cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE tenant_id = {tenant_id}")
        cnt_pending = cursor.fetchone()[0]
        if cnt_pending > 0:
            cursor.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE tenant_id = {tenant_id}")
        deleted_summary["platform.pending_uploads"] = cnt_pending

        # 12. Platform: pipeline_status
        cursor.execute(f"SELECT COUNT(1) FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE tenant_id = {tenant_id}")
        cnt_status = cursor.fetchone()[0]
        if cnt_status > 0:
            cursor.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE tenant_id = {tenant_id}")
        deleted_summary["platform.pipeline_status"] = cnt_status

        print("\n" + "=" * 75)
        print(f"CLEANUP SUMMARY FOR '{business_name}' (Tenant ID {tenant_id})")
        print("=" * 75)
        for tbl, count in deleted_summary.items():
            print(f"  - {tbl:<38}: {count:>6} rows removed")
        total_removed = sum(deleted_summary.values())
        print("-" * 75)
        print(f"  TOTAL ROWS REMOVED                   : {total_removed:>6} rows")
        print("=" * 75)
        print(f"Tenant {tenant_id} ('{business_name}') runtime state has been cleanly reset.")
        print("The demo organization remains registered and ready for repeat evaluations.")


if __name__ == "__main__":
    main()
