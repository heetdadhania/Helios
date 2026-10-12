import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.db.base import databricks_cursor

def main():
    with databricks_cursor() as cur:
        # Check tenants columns
        cur.execute("DESCRIBE TABLE `helios_catalog`.`platform`.`tenants`")
        t_cols = [r[0] for r in cur.fetchall()]
        print("Tenants columns:", t_cols)

        # Check users columns
        cur.execute("DESCRIBE TABLE `helios_catalog`.`platform`.`users`")
        u_cols = [r[0] for r in cur.fetchall()]
        print("Users columns:", u_cols)

        # Check tenant count
        cur.execute("SELECT count(*) FROM `helios_catalog`.`platform`.`tenants`")
        print("Tenant count:", cur.fetchone()[0])

        # Check users count
        cur.execute("SELECT count(*) FROM `helios_catalog`.`platform`.`users`")
        print("User count:", cur.fetchone()[0])

        # Check Bronze counts
        for tid in range(1, 11):
            cur.execute(f"SELECT count(*) FROM `helios_catalog`.`bronze`.`raw_orders` WHERE tenant_id = {tid}")
            c_raw = cur.fetchone()[0]
            cur.execute(f"SELECT count(*) FROM `helios_catalog`.`gold`.`fact_orders` WHERE tenant_id = {tid}")
            c_gold = cur.fetchone()[0]
            print(f"Tenant {tid}: Bronze raw_orders = {c_raw}, Gold fact_orders = {c_gold}")

if __name__ == "__main__":
    main()
