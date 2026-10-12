import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
load_dotenv(REPO_ROOT / "backend" / ".env")

from app.db.base import get_databricks_connection
from app.core.config import settings

catalog = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
print(f"Connecting to catalog {catalog}...")
with get_databricks_connection(catalog=catalog) as conn:
    with conn.cursor() as cur:
        with open(REPO_ROOT / "database" / "meta" / "03_audit_trail.sql") as f:
            sql_text = f.read().replace("USE CATALOG helios;", f"USE CATALOG `{catalog}`;").replace("helios.meta.", f"`{catalog}`.`meta`.")
        for stmt in sql_text.split(";"):
            s = stmt.strip()
            if s:
                cur.execute(s)
        cur.execute(f"DESCRIBE `{catalog}`.`meta`.`audit_trail`")
        cols = [r[0] for r in cur.fetchall()]
        print(f"meta.audit_trail table ready! Columns: {cols}")
