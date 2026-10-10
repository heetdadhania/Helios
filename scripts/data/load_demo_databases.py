#!/usr/bin/env python3
"""
Helios Data Platform - Demo Database Loader Script

Loads synthetic demo datasets into demo source databases for live demonstrations
of the Team Member Database Connection ingestion workflow:
  - Tenant 6 (Page & Quill Publishing): loads scripts/output/tenant_6_orders.csv into PostgreSQL
  - Tenant 7 (WonderKite Toyworks): loads scripts/output/tenant_7_orders.csv into MySQL

========================================================================================
CONNECTION DETAILS TO ENTER IN THE HELIOS "DATABASE CONNECTION" FORM:
========================================================================================
A) When Helios backend runs INSIDE Docker (e.g. via docker compose up):
   1. PostgreSQL (Tenant 6):
      - Database Engine: PostgreSQL
      - Host: demo-postgres
      - Port: 5432
      - Database Name: helios_demo_orders (or $DEMO_PG_DB)
      - Username: helios_pg (or $DEMO_PG_USER)
      - Password: helios_demo_pg_secret (or $DEMO_PG_PASSWORD)
      - Table or Query: orders

   2. MySQL (Tenant 7):
      - Database Engine: MySQL
      - Host: demo-mysql
      - Port: 3306
      - Database Name: helios_demo_orders (or $DEMO_MYSQL_DB)
      - Username: helios_mysql (or $DEMO_MYSQL_USER)
      - Password: helios_demo_mysql_secret (or $DEMO_MYSQL_PASSWORD)
      - Table or Query: orders

B) When Helios backend runs OUTSIDE Docker (e.g. uvicorn app.main:app on host):
   1. PostgreSQL (Tenant 6):
      - Host: localhost
      - Port: 5433 (mapped host port)
      - Database Name: helios_demo_orders
      - Username: helios_pg
      - Password: helios_demo_pg_secret
      - Table or Query: orders

   2. MySQL (Tenant 7):
      - Host: localhost
      - Port: 3307 (mapped host port)
      - Database Name: helios_demo_orders
      - Username: helios_mysql
      - Password: helios_demo_mysql_secret
      - Table or Query: orders

NOTE: Microsoft SQL Server is supported in application code (via pymssql in
backend/app/services/db_connection_service.py) but is not containerized here
due to the heavy Docker image size (>1.5 GB).
========================================================================================

Usage:
    python scripts/data/load_demo_databases.py [--batch-size 1000] [--pg-only] [--mysql-only]
"""

import argparse
import csv
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup repository paths
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load environment variables
from dotenv import load_dotenv

for env_path in [
    REPO_ROOT / ".env",
    REPO_ROOT / "backend" / ".env",
    Path.cwd() / ".env",
]:
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("helios.data.load_demo_db")

# Import DB drivers
try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    psycopg2 = None
    execute_batch = None

try:
    import mysql.connector
except ImportError:
    mysql = None


# -----------------------------------------------------------------------------
# Configuration from Environment Variables
# -----------------------------------------------------------------------------
PG_CONFIG = {
    "host": os.getenv("DEMO_PG_HOST", "localhost"),
    "port": int(os.getenv("DEMO_PG_PORT", "5433")),
    "user": os.getenv("DEMO_PG_USER", "helios_pg"),
    "password": os.getenv("DEMO_PG_PASSWORD", "helios_demo_pg_secret"),
    "dbname": os.getenv("DEMO_PG_DB", "helios_demo_orders"),
}

MYSQL_CONFIG = {
    "host": os.getenv("DEMO_MYSQL_HOST", "localhost"),
    "port": int(os.getenv("DEMO_MYSQL_PORT", "3307")),
    "user": os.getenv("DEMO_MYSQL_USER", "helios_mysql"),
    "password": os.getenv("DEMO_MYSQL_PASSWORD", "helios_demo_mysql_secret"),
    "database": os.getenv("DEMO_MYSQL_DB", "helios_demo_orders"),
}

COLUMNS = [
    "order_id",
    "order_date",
    "customer_name",
    "product_name",
    "category",
    "quantity",
    "unit_price",
    "discount",
    "total",
    "shipping_mode",
    "delivery_status",
    "scheduled_days",
    "actual_days",
]


def _read_and_transform_csv(csv_path: Path) -> List[Tuple[Any, ...]]:
    """Read tenant CSV and transform rows into tuple format matching the orders table schema."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Source CSV file not found: {csv_path}")

    records: List[Tuple[Any, ...]] = []
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Map DataCo/Synthetic CSV columns to table columns
            order_id = str(row.get("Order Id", "")).strip()
            order_date = str(row.get("order date (DateOrders)", "")).strip()

            fname = row.get("Customer Fname", "") or ""
            lname = row.get("Customer Lname", "") or ""
            customer_name = f"{fname} {lname}".strip() or "Customer"

            product_name = str(row.get("Product Name", "")).strip()
            category = str(row.get("Category Name", "")).strip()

            # Preserve raw quantities (including blanks/negatives for dirty data demo)
            raw_qty = row.get("Order Item Quantity")
            quantity = str(raw_qty).strip() if raw_qty is not None else ""

            unit_price = str(row.get("Order Item Product Price", "")).strip()
            discount = str(row.get("Order Item Discount", "")).strip()
            total = str(row.get("Order Item Total", "")).strip()

            shipping_mode = str(row.get("Shipping Mode", "")).strip()
            delivery_status = str(row.get("Delivery Status", "")).strip()

            raw_sched = row.get("Days for shipment (scheduled)")
            try:
                scheduled_days = int(float(raw_sched)) if raw_sched is not None and str(raw_sched).strip() != "" else None
            except (ValueError, TypeError):
                scheduled_days = None

            raw_actual = row.get("Days for shipping (real)")
            try:
                actual_days = int(float(raw_actual)) if raw_actual is not None and str(raw_actual).strip() != "" else None
            except (ValueError, TypeError):
                actual_days = None

            records.append((
                order_id,
                order_date,
                customer_name,
                product_name,
                category,
                quantity,
                unit_price,
                discount,
                total,
                shipping_mode,
                delivery_status,
                scheduled_days,
                actual_days,
            ))

    return records


def load_postgres(csv_path: Path, batch_size: int = 1000) -> int:
    """Load records into PostgreSQL demo-postgres orders table."""
    if psycopg2 is None:
        logger.error("psycopg2 is not installed. Run: pip install psycopg2-binary")
        return 0

    logger.info("Connecting to PostgreSQL at %s:%d/%s...", PG_CONFIG["host"], PG_CONFIG["port"], PG_CONFIG["dbname"])
    try:
        conn = psycopg2.connect(
            host=PG_CONFIG["host"],
            port=PG_CONFIG["port"],
            user=PG_CONFIG["user"],
            password=PG_CONFIG["password"],
            dbname=PG_CONFIG["dbname"],
            connect_timeout=10,
        )
    except Exception as exc:
        logger.error("Failed to connect to PostgreSQL: %s", exc)
        logger.info("Make sure the docker container is running: docker compose up -d demo-postgres")
        return 0

    try:
        cur = conn.cursor()

        # Ensure table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR(50),
                order_date VARCHAR(50),
                customer_name VARCHAR(255),
                product_name VARCHAR(255),
                category VARCHAR(100),
                quantity VARCHAR(50),
                unit_price VARCHAR(50),
                discount VARCHAR(50),
                total VARCHAR(50),
                shipping_mode VARCHAR(100),
                delivery_status VARCHAR(100),
                scheduled_days INT,
                actual_days INT
            );
        """)

        # Truncate table for idempotent demo reload
        cur.execute("TRUNCATE TABLE orders;")
        conn.commit()

        records = _read_and_transform_csv(csv_path)
        logger.info("Loaded %d records from %s. Inserting into PostgreSQL in batches of %d...", len(records), csv_path.name, batch_size)

        insert_sql = f"""
            INSERT INTO orders ({", ".join(COLUMNS)})
            VALUES ({", ".join(["%s"] * len(COLUMNS))});
        """

        total_inserted = 0
        start_time = time.time()

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            execute_batch(cur, insert_sql, batch)
            conn.commit()
            total_inserted += len(batch)
            logger.info("  PostgreSQL: %d / %d rows inserted", total_inserted, len(records))

        elapsed = time.time() - start_time
        logger.info("Successfully loaded %d rows into PostgreSQL orders table (%.2fs)", total_inserted, elapsed)
        cur.close()
        return total_inserted
    finally:
        conn.close()


def load_mysql(csv_path: Path, batch_size: int = 1000) -> int:
    """Load records into MySQL demo-mysql orders table."""
    if mysql is None:
        logger.error("mysql-connector-python is not installed. Run: pip install mysql-connector-python")
        return 0

    logger.info("Connecting to MySQL at %s:%d/%s...", MYSQL_CONFIG["host"], MYSQL_CONFIG["port"], MYSQL_CONFIG["database"])
    try:
        conn = mysql.connector.connect(
            host=MYSQL_CONFIG["host"],
            port=MYSQL_CONFIG["port"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"],
            connection_timeout=10,
        )
    except Exception as exc:
        logger.error("Failed to connect to MySQL: %s", exc)
        logger.info("Make sure the docker container is running: docker compose up -d demo-mysql")
        return 0

    try:
        cur = conn.cursor()

        # Ensure table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR(50),
                order_date VARCHAR(50),
                customer_name VARCHAR(255),
                product_name VARCHAR(255),
                category VARCHAR(100),
                quantity VARCHAR(50),
                unit_price VARCHAR(50),
                discount VARCHAR(50),
                total VARCHAR(50),
                shipping_mode VARCHAR(100),
                delivery_status VARCHAR(100),
                scheduled_days INT,
                actual_days INT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # Truncate table for idempotent demo reload
        cur.execute("TRUNCATE TABLE orders;")
        conn.commit()

        records = _read_and_transform_csv(csv_path)
        logger.info("Loaded %d records from %s. Inserting into MySQL in batches of %d...", len(records), csv_path.name, batch_size)

        insert_sql = f"""
            INSERT INTO orders ({", ".join(COLUMNS)})
            VALUES ({", ".join(["%s"] * len(COLUMNS))});
        """

        total_inserted = 0
        start_time = time.time()

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            cur.executemany(insert_sql, batch)
            conn.commit()
            total_inserted += len(batch)
            logger.info("  MySQL: %d / %d rows inserted", total_inserted, len(records))

        elapsed = time.time() - start_time
        logger.info("Successfully loaded %d rows into MySQL orders table (%.2fs)", total_inserted, elapsed)
        cur.close()
        return total_inserted
    finally:
        conn.close()


def print_connection_documentation() -> None:
    """Print documentation table of connection parameters for Team Member form."""
    print("""
========================================================================================
            TEAM MEMBER DATABASE CONNECTION FORM - CHEAT SHEET
========================================================================================
To ingest live demo database data in Helios, navigate to:
  Data Ingestion -> Database Connection -> Add Database Connection

----------------------------------------------------------------------------------------
Option 1: TENANT 6 (Page & Quill Publishing) -> PostgreSQL
----------------------------------------------------------------------------------------
  - Tenant:             Tenant 6 (Page & Quill Publishing)
  - Database Engine:    PostgreSQL
  - Host:               demo-postgres (if backend is in Docker) OR localhost (if host)
  - Port:               5432 (inside Docker) OR 5433 (outside Docker on localhost)
  - Database Name:      helios_demo_orders
  - Username:           helios_pg
  - Password:           helios_demo_pg_secret
  - Table or Query:     orders

----------------------------------------------------------------------------------------
Option 2: TENANT 7 (WonderKite Toyworks) -> MySQL
----------------------------------------------------------------------------------------
  - Tenant:             Tenant 7 (WonderKite Toyworks)
  - Database Engine:    MySQL
  - Host:               demo-mysql (if backend is in Docker) OR localhost (if host)
  - Port:               3306 (inside Docker) OR 3307 (outside Docker on localhost)
  - Database Name:      helios_demo_orders
  - Username:           helios_mysql
  - Password:           helios_demo_mysql_secret
  - Table or Query:     orders

* NOTE: Microsoft SQL Server is supported in application code (via pymssql)
  but is not containerized in demo environment due to Docker image size (>1.5 GB).
========================================================================================
""")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load demo synthetic order CSVs into PostgreSQL and MySQL demo databases")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch insertion size (default: 1000)")
    parser.add_argument("--pg-only", action="store_true", help="Only load PostgreSQL (Tenant 6)")
    parser.add_argument("--mysql-only", action="store_true", help="Only load MySQL (Tenant 7)")
    parser.add_argument("--info", action="store_true", help="Print connection form documentation and exit")
    args = parser.parse_args()

    if args.info:
        print_connection_documentation()
        return

    output_dir = REPO_ROOT / "scripts" / "output"
    t6_csv = output_dir / "tenant_6_orders.csv"
    t7_csv = output_dir / "tenant_7_orders.csv"

    pg_loaded = 0
    my_loaded = 0

    if not args.mysql_only:
        if not t6_csv.is_file():
            logger.error("Tenant 6 CSV not found at %s. Please run scripts/data/generate_synthetic_tenants.py first.", t6_csv)
        else:
            pg_loaded = load_postgres(t6_csv, batch_size=args.batch_size)

    if not args.pg_only:
        if not t7_csv.is_file():
            logger.error("Tenant 7 CSV not found at %s. Please run scripts/data/generate_synthetic_tenants.py first.", t7_csv)
        else:
            my_loaded = load_mysql(t7_csv, batch_size=args.batch_size)

    print("\n" + "=" * 60)
    print(" DEMO DATABASE LOADING SUMMARY ".center(60))
    print("=" * 60)
    print(f"  PostgreSQL (Tenant 6, Books): {pg_loaded:,} rows loaded into 'orders'")
    print(f"  MySQL      (Tenant 7, Toys):  {my_loaded:,} rows loaded into 'orders'")
    print("=" * 60)

    print_connection_documentation()


if __name__ == "__main__":
    main()
