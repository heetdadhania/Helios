#!/usr/bin/env python3
"""
Helios Data Platform - Demo Tenant Data Preparation Script

Splits the DataCo Smart Supply Chain dataset into 2-3 isolated tenant CSVs,
simulating multiple distinct e-commerce businesses:
  - Tenant 1: Apex Consumer Goods (Market: Europe, Segment: Consumer)
  - Tenant 2: Pacific Tech & Corporate (Market: Pacific Asia, Segment: Corporate)
  - Tenant 3: Vanguard Home Office (Market: USCA, Segment: Home Office)

If no raw DataCo CSV file is provided, this script includes a realistic synthetic
generator adhering strictly to the 53-column DataCo supply chain schema.
"""

import argparse
import csv
import io
import logging
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("helios.demo.prepare_tenants")

# Canonical DataCo Smart Supply Chain Dataset column names (53 columns)
DATACO_COLUMNS: List[str] = [
    "Type",
    "Days for shipping (real)",
    "Days for shipment (scheduled)",
    "Benefit per order",
    "Sales per customer",
    "Delivery Status",
    "Late_delivery_risk",
    "Category Id",
    "Category Name",
    "Customer City",
    "Customer Country",
    "Customer Email",
    "Customer Fname",
    "Customer Id",
    "Customer Lname",
    "Customer Password",
    "Customer Segment",
    "Customer State",
    "Customer Street",
    "Customer Zipcode",
    "Department Id",
    "Department Name",
    "Latitude",
    "Longitude",
    "Market",
    "Order City",
    "Order Country",
    "Order Customer Id",
    "order date (DateOrders)",
    "Order Id",
    "Order Item Cardprod Id",
    "Order Item Discount",
    "Order Item Discount Rate",
    "Order Item Id",
    "Order Item Product Price",
    "Order Item Profit Ratio",
    "Order Item Quantity",
    "Sales",
    "Order Item Total",
    "Order Profit Per Order",
    "Order Region",
    "Order State",
    "Order Status",
    "Order Zipcode",
    "Product Card Id",
    "Product Category Id",
    "Product Description",
    "Product Image",
    "Product Name",
    "Product Price",
    "Product Status",
    "shipping date (DateOrders)",
    "Shipping Mode",
]

# Tenant specifications for splitting
TENANT_SPECS: List[Dict[str, Any]] = [
    {
        "tenant_id": 1,
        "name": "Apex Consumer Goods",
        "market": "Europe",
        "segment": "Consumer",
        "filename": "tenant_1_apex_consumer.csv",
        "industry": "Apparel & Lifestyle",
    },
    {
        "tenant_id": 2,
        "name": "Pacific Tech & Corporate",
        "market": "Pacific Asia",
        "segment": "Corporate",
        "filename": "tenant_2_pacific_tech.csv",
        "industry": "Consumer Electronics & IT",
    },
    {
        "tenant_id": 3,
        "name": "Vanguard Home Office",
        "market": "USCA",
        "segment": "Home Office",
        "filename": "tenant_3_vanguard_home.csv",
        "industry": "Office Supplies & Furniture",
    },
]


def detect_file_encoding(file_path: Path) -> str:
    """Attempt reading with common encodings used by DataCo datasets."""
    encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252", "iso-8859-1"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, OSError):
            continue
    return "latin1"


def generate_synthetic_dataco_rows(
    tenant_spec: Dict[str, Any],
    row_count: int = 500,
) -> List[Dict[str, Any]]:
    """
    Synthesize realistic DataCo supply chain order rows matching the schema
    and tailored to the tenant's market and customer segment.
    """
    random.seed(tenant_spec["tenant_id"] * 42)
    rows: List[Dict[str, Any]] = []

    market = tenant_spec["market"]
    segment = tenant_spec["segment"]

    # Tenant-specific catalogs
    catalogs = {
        "Consumer": [
            ("Footwear", "Nike Men's Free 5.0 Running Shoes", 129.99),
            ("Apparel", "Adidas Women's ClimaChill T-Shirt", 45.00),
            ("Accessories", "Under Armour Hustle Backpack", 55.00),
            ("Sporting Goods", "Callaway 2018 Golf Ball 12-Pack", 32.50),
            ("Footwear", "Puma Men's Ignite Evoknit Lo", 99.95),
        ],
        "Corporate": [
            ("Computers", "Dell UltraSharp 27-inch 4K Monitor", 449.99),
            ("Electronics", "Logitech MX Master 3S Wireless Mouse", 99.99),
            ("Hardware", "Cisco Catalyst 24-Port Gigabit Switch", 599.00),
            ("Electronics", "Bose Noise Cancelling Headphones 700", 379.00),
            ("Computers", "Lenovo ThinkPad Thunderbolt 4 Dock", 289.50),
        ],
        "Home Office": [
            ("Furniture", "Ergonomic Mesh Office Executive Chair", 249.99),
            ("Office Equipment", "HP LaserJet Pro Multifunction Printer", 329.00),
            ("Accessories", "Vari Electric Standing Desk 48x30", 550.00),
            ("Office Supplies", "Fellowes Powershred 12-Sheet Cross-Cut", 139.95),
            ("Lighting", "BenQ ScreenBar e-Reading LED Lamp", 109.00),
        ],
    }

    catalog = catalogs.get(segment, catalogs["Consumer"])
    cities_by_market = {
        "Europe": ["London", "Berlin", "Paris", "Madrid", "Rome", "Amsterdam", "Dublin"],
        "Pacific Asia": ["Tokyo", "Singapore", "Sydney", "Seoul", "Hong Kong", "Melbourne"],
        "USCA": ["New York", "Los Angeles", "Chicago", "Toronto", "Vancouver", "Seattle"],
    }
    cities = cities_by_market.get(market, ["Springfield"])
    shipping_modes = ["Standard Class", "Second Class", "First Class", "Same Day"]
    order_statuses = ["COMPLETE", "CLOSED", "PENDING", "PROCESSING", "ON_HOLD", "CANCELED"]

    base_time = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)

    for i in range(1, row_count + 1):
        order_id = 100000 + (tenant_spec["tenant_id"] * 10000) + i
        item_id = 200000 + (tenant_spec["tenant_id"] * 10000) + i
        cust_id = 3000 + (tenant_spec["tenant_id"] * 500) + (i % 75)

        category, product_name, price = random.choice(catalog)
        qty = random.randint(1, 4) if segment == "Consumer" else random.randint(1, 10)
        discount_rate = round(random.choice([0.0, 0.05, 0.10, 0.15, 0.20]), 2)
        total = round(price * qty * (1.0 - discount_rate), 2)
        profit_ratio = round(random.uniform(0.12, 0.38), 2)
        profit = round(total * profit_ratio, 2)

        order_time = base_time + timedelta(hours=i * 2, minutes=random.randint(0, 59))
        sched_days = random.randint(2, 6)
        is_late = random.random() < 0.28
        real_days = sched_days + (random.randint(1, 3) if is_late else random.randint(-1, 0))
        real_days = max(1, real_days)

        ship_time = order_time + timedelta(days=real_days)
        delivery_status = "Late delivery" if is_late else "Advance shipping"

        row = {
            "Type": random.choice(["DEBIT", "TRANSFER", "PAYMENT", "CASH"]),
            "Days for shipping (real)": real_days,
            "Days for shipment (scheduled)": sched_days,
            "Benefit per order": profit,
            "Sales per customer": total,
            "Delivery Status": delivery_status,
            "Late_delivery_risk": 1 if is_late else 0,
            "Category Id": hash(category) % 100 + 1,
            "Category Name": category,
            "Customer City": random.choice(cities),
            "Customer Country": market,
            "Customer Email": f"user{cust_id}@{tenant_spec['name'].lower().replace(' ', '')}.com",
            "Customer Fname": f"First{cust_id}",
            "Customer Id": cust_id,
            "Customer Lname": f"Last{cust_id}",
            "Customer Password": "********",
            "Customer Segment": segment,
            "Customer State": f"State-{random.choice(cities)}",
            "Customer Street": f"{random.randint(100, 999)} Commerce Ave",
            "Customer Zipcode": str(random.randint(10000, 99999)),
            "Department Id": random.randint(1, 10),
            "Department Name": "Retail Sales",
            "Latitude": round(random.uniform(25.0, 55.0), 4),
            "Longitude": round(random.uniform(-120.0, 140.0), 4),
            "Market": market,
            "Order City": random.choice(cities),
            "Order Country": market,
            "Order Customer Id": cust_id,
            "order date (DateOrders)": order_time.strftime("%m/%d/%Y %H:%M"),
            "Order Id": order_id,
            "Order Item Cardprod Id": random.randint(50, 500),
            "Order Item Discount": round(price * qty * discount_rate, 2),
            "Order Item Discount Rate": discount_rate,
            "Order Item Id": item_id,
            "Order Item Product Price": price,
            "Order Item Profit Ratio": profit_ratio,
            "Order Item Quantity": qty,
            "Sales": round(price * qty, 2),
            "Order Item Total": total,
            "Order Profit Per Order": profit,
            "Order Region": f"{market} Central",
            "Order State": f"{random.choice(cities)} Region",
            "Order Status": random.choice(order_statuses),
            "Order Zipcode": str(random.randint(10000, 99999)),
            "Product Card Id": random.randint(50, 500),
            "Product Category Id": hash(category) % 100 + 1,
            "Product Description": f"Premium quality {product_name}",
            "Product Image": f"https://images.helios.io/products/{item_id}.jpg",
            "Product Name": product_name,
            "Product Price": price,
            "Product Status": 0,
            "shipping date (DateOrders)": ship_time.strftime("%m/%d/%Y %H:%M"),
            "Shipping Mode": random.choice(shipping_modes),
        }
        rows.append(row)

    return rows


def split_dataco_csv(
    input_csv_path: Path,
    output_dir: Path,
    max_rows_per_tenant: Optional[int] = None,
) -> Dict[int, Path]:
    """
    Read an existing DataCo CSV file and partition into tenant-specific CSV files
    matching the market and segment filters.
    """
    encoding = detect_file_encoding(input_csv_path)
    logger.info("Reading input DataCo CSV from %s (encoding: %s)", input_csv_path, encoding)

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: Dict[int, Path] = {}

    # Read header and filter rows
    with open(input_csv_path, "r", encoding=encoding, errors="replace") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames or DATACO_COLUMNS

        # Buckets for each tenant
        tenant_rows: Dict[int, List[Dict[str, Any]]] = {spec["tenant_id"]: [] for spec in TENANT_SPECS}

        for row in reader:
            market = (row.get("Market") or "").strip()
            segment = (row.get("Customer Segment") or "").strip()

            for spec in TENANT_SPECS:
                t_id = spec["tenant_id"]
                if max_rows_per_tenant and len(tenant_rows[t_id]) >= max_rows_per_tenant:
                    continue

                # Match by market & segment, or market alone as fallback
                if (spec["market"] == market and spec["segment"] == segment) or (
                    spec["market"] == market and len(tenant_rows[t_id]) < 50
                ):
                    tenant_rows[t_id].append(row)
                    break

        # If any tenant did not find enough records, fill with matching market rows
        for spec in TENANT_SPECS:
            t_id = spec["tenant_id"]
            out_file = output_dir / spec["filename"]
            rows_to_write = tenant_rows[t_id]

            # If real CSV had 0 rows for this combination, generate synthetic subset
            if not rows_to_write:
                logger.warning(
                    "No matching rows in %s for %s (%s/%s). Generating synthetic rows.",
                    input_csv_path.name,
                    spec["name"],
                    spec["market"],
                    spec["segment"],
                )
                rows_to_write = generate_synthetic_dataco_rows(spec, row_count=max_rows_per_tenant or 300)

            with open(out_file, "w", encoding="utf-8", newline="") as outfile:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows_to_write)

            total_sales = sum(float(r.get("Sales", 0) or 0) for r in rows_to_write)
            logger.info(
                "Tenant %d [%s]: wrote %d rows (Total Sales: $%.2f) -> %s",
                t_id,
                spec["name"],
                len(rows_to_write),
                total_sales,
                out_file,
            )
            generated_files[t_id] = out_file

    return generated_files


def generate_all_synthetic_tenants(
    output_dir: Path,
    rows_per_tenant: int = 500,
) -> Dict[int, Path]:
    """Generate all 3 tenant datasets synthetically."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: Dict[int, Path] = {}

    for spec in TENANT_SPECS:
        t_id = spec["tenant_id"]
        out_file = output_dir / spec["filename"]
        rows = generate_synthetic_dataco_rows(spec, row_count=rows_per_tenant)

        with open(out_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=DATACO_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

        total_sales = sum(float(r["Sales"]) for r in rows)
        logger.info(
            "Synthesized Tenant %d [%s]: %d rows (Sales: $%.2f) -> %s",
            t_id,
            spec["name"],
            len(rows),
            total_sales,
            out_file,
        )
        generated_files[t_id] = out_file

    return generated_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Helios Demo Tenant Data Preparation")
    parser.add_argument(
        "--input-csv",
        type=str,
        default=None,
        help="Path to raw DataCo CSV file (e.g. DataCoSupplyChainDataset.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/demo",
        help="Target output directory for tenant CSVs (default: data/demo)",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=500,
        help="Maximum rows per tenant file (default: 500)",
    )
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Force synthetic DataCo generation without searching for local dataset",
    )

    args = parser.parse_args()
    out_path = Path(args.output_dir)

    # Determine execution mode
    if args.synthetic_only or not args.input_csv:
        # Check if a DataCo file exists in common locations
        common_locations = [
            Path("DataCoSupplyChainDataset.csv"),
            Path("data/DataCoSupplyChainDataset.csv"),
            Path("pipeline/demo/DataCoSupplyChainDataset.csv"),
        ]
        found_file = next((p for p in common_locations if p.is_file()), None)

        if found_file and not args.synthetic_only:
            logger.info("Found existing DataCo dataset at %s", found_file)
            split_dataco_csv(found_file, out_path, max_rows_per_tenant=args.max_rows)
        else:
            logger.info("Generating realistic synthetic DataCo demo datasets...")
            generate_all_synthetic_tenants(out_path, rows_per_tenant=args.max_rows)
    else:
        csv_file = Path(args.input_csv)
        if not csv_file.is_file():
            logger.error("Input CSV file '%s' does not exist.", args.input_csv)
            sys.exit(1)
        split_dataco_csv(csv_file, out_path, max_rows_per_tenant=args.max_rows)

    logger.info("Demo tenant data preparation complete!")


if __name__ == "__main__":
    main()
