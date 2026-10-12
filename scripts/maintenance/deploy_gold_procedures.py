import re
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
PROCEDURES_DIR = REPO_ROOT / "database" / "gold" / "procedures"

proc_files = sorted(list(PROCEDURES_DIR.glob("*.sql")))
print(f"Deploying {len(proc_files)} Gold procedures to {CATALOG}...")

with databricks_cursor() as cur:
    for f in proc_files:
        print(f"\nProcessing {f.name}...")
        content = f.read_text(encoding="utf-8")
        # Replace catalog
        content = re.sub(r"\bhelios\b", CATALOG, content)
        
        # We need to extract the CREATE OR REPLACE PROCEDURE statement
        # Strip USE CATALOG / USE SCHEMA lines or comments
        lines = []
        in_proc = False
        for line in content.splitlines():
            trimmed = line.strip()
            if trimmed.upper().startswith("USE CATALOG") or trimmed.upper().startswith("USE SCHEMA"):
                continue
            if trimmed.upper().startswith("CREATE OR REPLACE PROCEDURE"):
                in_proc = True
            if in_proc:
                lines.append(line)
        
        proc_sql = "\n".join(lines).strip()
        if proc_sql.endswith(";"):
            proc_sql = proc_sql[:-1].strip()
            
        try:
            cur.execute(f"USE CATALOG {CATALOG}")
            cur.execute(f"USE SCHEMA gold")
            cur.execute(proc_sql)
            print(f"  SUCCESS: {f.name}")
        except Exception as e:
            print(f"  ERROR in {f.name}: {e}")

print("\nVerifying procedures...")
with databricks_cursor() as cur:
    for f in proc_files:
        p_name = f.stem.split("_", 1)[1] if "_" in f.stem else f.stem
        try:
            cur.execute(f"DESCRIBE PROCEDURE {CATALOG}.gold.{p_name}")
            print(f"  {p_name:30}: VERIFIED")
        except Exception as e:
            print(f"  {p_name:30}: FAILED ({e})")
