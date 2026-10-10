#!/usr/bin/env python3
"""
Helios Data Platform - Synthetic Tenant Data Generator (Tenants 4-10)

Generates realistic order and shipping demo datasets using Faker and DataCo-like schema:
  - Tenant 4: Stable, medium volume, ~6,000 rows (Excel .xlsx, fuzzy headers)
  - Tenant 5: Seasonal, peaks in Nov/Dec, ~8,000 rows (Excel .xlsx, fuzzy headers)
  - Tenant 6: Growing steadily, ~10,000 rows (CSV)
  - Tenant 7: Declining steadily, ~7,000 rows (CSV, flags Critical in Tenant Health with high late-delivery rate)
  - Tenant 8: Small, ~2,000 rows (CSV)
  - Tenant 9: Large, ~15,000 rows (CSV)
  - Tenant 10: Stable, high discount rate & low profit, ~5,000 rows (CSV)

Rules:
  - Dates end within the last 7 days before today and span 6 to 12 months.
  - ~3% of rows deliberately bad (null quantities, duplicate lines, mixed date formats,
    currency strings like '$1,250.00', negative quantities).
  - Excel headers for T4 and T5 renamed to fuzzy variants (Cust_Name, Order_Dt, Qty, etc.).
  - Output .xlsx for T4-5 (openpyxl) and .csv for T6-10.
  - Uses fixed random seeds so runs are fully deterministic and reproducible.

Usage:
    python scripts/data/generate_synthetic_tenants.py [--output-dir scripts/output]
"""

import argparse
import csv
import logging
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from faker import Faker

# Ensure repo root is on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.data.common import (
    DATACO_COLUMNS,
    DEFAULT_SEED,
    extract_date_range,
    generate_date_range,
    get_output_dir,
    inject_bad_rows,
    print_summary_table,
    set_random_seed,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("helios.data.generate_synthetic")

# Fuzzy column variants for Excel tenants (4 and 5)
EXCEL_ORDERS_HEADER_MAP = {
    "Customer Fname": "Cust_Name",
    "order date (DateOrders)": "Order_Dt",
    "Order Item Quantity": "Qty",
    "Order Item Total": "Total_Amount",
    "Order Item Product Price": "Unit_Price",
}

EXCEL_SHIPPING_HEADER_MAP = {
    "Customer Fname": "Cust_Name",
    "order date (DateOrders)": "Order_Dt",
    "shipping date (DateOrders)": "Ship_Date",
    "Shipping Mode": "Ship_Mode",
    "Delivery Status": "Status",
}

SYNTHETIC_TENANT_CONFIGS = [
    {
        "tenant_id": 4,
        "name": "Velvet Botanicals",
        "industry": "Beauty",
        "target_rows": 6000,
        "format": "xlsx",
        "shape": "stable",
        "late_rate": 0.08,
        "avg_discount": 0.08,
        "profit_margin": (0.20, 0.45),
        "seed": DEFAULT_SEED + 400,
        "orders_file": "tenant_4_orders.xlsx",
        "shipping_file": "tenant_4_shipping.xlsx",
        "catalog": [
            ("Skincare", "Organic Rosewater Hydrating Mist", 32.00),
            ("Skincare", "Botanical Ceramide Barrier Cream", 58.00),
            ("Haircare", "Argan & Marula Restorative Hair Oil", 42.00),
            ("Fragrance", "Smoky Vetiver & Bergamot Parfum", 95.00),
            ("Body", "Dead Sea Mineral Body Polish", 36.50),
            ("Skincare", "Vitamin C Brightening Elixir", 64.00),
            ("Wellness", "Lavender Night Calming Balm", 28.00),
        ],
    },
    {
        "tenant_id": 5,
        "name": "Summit Peak Athletics",
        "industry": "Sports",
        "target_rows": 8000,
        "format": "xlsx",
        "shape": "seasonal_q4",  # Heavy peaks in November/December
        "late_rate": 0.12,
        "avg_discount": 0.12,
        "profit_margin": (0.18, 0.38),
        "seed": DEFAULT_SEED + 500,
        "orders_file": "tenant_5_orders.xlsx",
        "shipping_file": "tenant_5_shipping.xlsx",
        "catalog": [
            ("Footwear", "TrailGrip GTX Mountain Running Shoes", 145.00),
            ("Apparel", "Thermal WindStopper Alpine Shell", 195.00),
            ("Equipment", "Ultralight Carbon Trekking Poles", 89.00),
            ("Accessories", "Hydration Vest Pack 12L", 115.00),
            ("Apparel", "Merino 260 Thermal Base Layer", 75.00),
            ("Winter Sports", "ProVision Anti-Fog Ski Goggles", 130.00),
            ("Equipment", "Four-Season Geodesic Summit Tent", 340.00),
        ],
    },
    {
        "tenant_id": 6,
        "name": "Page & Quill Publishing",
        "industry": "Books",
        "target_rows": 10000,
        "format": "csv",
        "shape": "growing",  # Steady upward trend over the timeframe
        "late_rate": 0.07,
        "avg_discount": 0.05,
        "profit_margin": (0.22, 0.40),
        "seed": DEFAULT_SEED + 600,
        "orders_file": "tenant_6_orders.csv",
        "shipping_file": "tenant_6_shipping.csv",
        "catalog": [
            ("Fiction", "The Clockmaker of Antiquity Hardcover", 28.50),
            ("Non-Fiction", "Architectural Heritage of Europe", 45.00),
            ("Stationery", "Hand-Bound Full Grain Leather Journal", 38.00),
            ("Accessories", "Brass Fountain Pen Fine Nib", 62.00),
            ("Art & Poetry", "Illuminated Selected Verses Folio", 54.00),
            ("Children", "Atlas of Fantastic Creatures", 22.00),
            ("Philosophy", "Modern Meditations on Reason", 31.50),
        ],
    },
    {
        "tenant_id": 7,
        "name": "WonderKite Toyworks",
        "industry": "Toys",
        "target_rows": 7000,
        "format": "csv",
        "shape": "declining_critical",  # Steady decline + high late-delivery rate > 25% (SLA breach)
        "late_rate": 0.48,              # 48% late delivery rate flags Critical in Tenant Health
        "avg_discount": 0.15,
        "profit_margin": (0.10, 0.25),
        "seed": DEFAULT_SEED + 700,
        "orders_file": "tenant_7_orders.csv",
        "shipping_file": "tenant_7_shipping.csv",
        "catalog": [
            ("Building Toys", "Architectural Beechwood Block Set 120pc", 68.00),
            ("STEM", "Solar Powered Robotics Discovery Kit", 49.99),
            ("Outdoor Toys", "Ripstop Stunt Kite Dual-Line", 34.50),
            ("Puzzles", "Laser Cut 3D Mechanical Music Box", 42.00),
            ("Plush", "Handmade Organic Cotton Bear", 29.00),
            ("Board Games", "Expedition Terra Cooperative Game", 45.00),
            ("Crafts", "Pottery Studio Wheel & Glaze Kit", 55.00),
        ],
    },
    {
        "tenant_id": 8,
        "name": "Terra Verde Organics",
        "industry": "Grocery",
        "target_rows": 2000,
        "format": "csv",
        "shape": "small_stable",
        "late_rate": 0.06,
        "avg_discount": 0.04,
        "profit_margin": (0.15, 0.32),
        "seed": DEFAULT_SEED + 800,
        "orders_file": "tenant_8_orders.csv",
        "shipping_file": "tenant_8_shipping.csv",
        "catalog": [
            ("Pantry", "Single-Estate Extra Virgin Olive Oil 500ml", 26.50),
            ("Pantry", "Aged Modena IGP Balsamic Vinegar 12yr", 44.00),
            ("Beverages", "Highland Shade-Grown Whole Bean Coffee", 18.00),
            ("Gourmet", "Artisanal Bronze-Cut Semolina Pasta 1kg", 9.50),
            ("Snacks", "Raw Wildflower Honeycomb Jar", 16.50),
            ("Spices", "Organic Mediterranean Herb Medley", 12.00),
        ],
    },
    {
        "tenant_id": 9,
        "name": "Luminary Fine Gems",
        "industry": "Jewelry",
        "target_rows": 15000,
        "format": "csv",
        "shape": "large_high_volume",
        "late_rate": 0.09,
        "avg_discount": 0.06,
        "profit_margin": (0.28, 0.55),
        "seed": DEFAULT_SEED + 900,
        "orders_file": "tenant_9_orders.csv",
        "shipping_file": "tenant_9_shipping.csv",
        "catalog": [
            ("Necklaces", "Solitaire Diamond Pendant 18K Yellow Gold", 650.00),
            ("Rings", "Ceylon Sapphire Pavé Band Platinum", 880.00),
            ("Earrings", "Freshwater Baroque Pearl Drop Earrings", 240.00),
            ("Bracelets", "Hand-Braided Tennis Bracelet 14K Gold", 720.00),
            ("Watches", "Chronograph Automatic Sapphire Crystal", 1250.00),
            ("Rings", "Emerald Cut Eternity Ring White Gold", 920.00),
        ],
    },
    {
        "tenant_id": 10,
        "name": "Paws & Trails Outfitters",
        "industry": "Pet Supplies",
        "target_rows": 5000,
        "format": "csv",
        "shape": "high_discount_low_profit",  # Heavy discounting (>25%), thin profit margin (<5%)
        "late_rate": 0.10,
        "avg_discount": 0.32,                 # Average discount rate 32%
        "profit_margin": (0.01, 0.04),        # Razor thin profit margin 1% - 4%
        "seed": DEFAULT_SEED + 1000,
        "orders_file": "tenant_10_orders.csv",
        "shipping_file": "tenant_10_shipping.csv",
        "catalog": [
            ("Gear", "All-Terrain K9 Tactical Harness", 54.00),
            ("Gear", "Climbing Rope Bungee Running Leash", 28.00),
            ("Nutrition", "Freeze-Dried Venison & Berry Topper", 24.50),
            ("Outdoor", "Waterproof Packable Dog Sleeping Bag", 65.00),
            ("Travel", "Crash-Tested Automotive Safety Seat", 120.00),
            ("Care", "Paw Guard Natural All-Weather Wax", 15.00),
            ("Toys", "Indestructible Natural Rubber Fetch Stick", 18.00),
        ],
    },
]


def _sample_order_timestamp(
    shape: str,
    start_time: datetime,
    end_time: datetime,
    rng: random.Random,
) -> datetime:
    """Sample an order timestamp adhering to the tenant's specified business shape."""
    total_seconds = max(1.0, (end_time - start_time).total_seconds())

    if shape == "seasonal_q4":
        # 65% of orders concentrated in November and December
        if rng.random() < 0.65:
            # Pick a date in Nov or Dec within the window
            target_year = end_time.year if end_time.month >= 11 else end_time.year - 1
            nov_start = datetime(target_year, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
            dec_end = datetime(target_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

            # Ensure bounds fit within start_time and end_time
            clamped_start = max(start_time, nov_start)
            clamped_end = min(end_time, dec_end)
            if clamped_end > clamped_start:
                span = (clamped_end - clamped_start).total_seconds()
                return clamped_start + timedelta(seconds=rng.uniform(0, span))

        # Remainder uniform across the entire range
        return start_time + timedelta(seconds=rng.uniform(0, total_seconds))

    elif shape == "growing":
        # Steady upward growth: triangular distribution peaked at end
        # Random variable with pdf linear increasing: t = sqrt(u)
        u = rng.random()
        fraction = u ** 0.55  # skew toward recent dates
        return start_time + timedelta(seconds=fraction * total_seconds)

    elif shape == "declining_critical":
        # Steady downward decline: triangular distribution peaked at start
        u = rng.random()
        fraction = 1.0 - (u ** 0.55)  # skew toward older dates
        return start_time + timedelta(seconds=fraction * total_seconds)

    else:
        # Standard uniform stable distribution
        return start_time + timedelta(seconds=rng.uniform(0, total_seconds))


def generate_tenant_records(
    config: Dict[str, Any],
    start_time: datetime,
    end_time: datetime,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generate order and shipping records for a single synthetic tenant.
    Returns (raw_orders, raw_shipping) before bad-row injection and formatting.
    """
    rng = random.Random(config["seed"])
    fake = Faker()
    fake.seed_instance(config["seed"])

    tenant_id = config["tenant_id"]
    target_rows = config["target_rows"]
    catalog = config["catalog"]
    shape = config["shape"]
    late_rate = config["late_rate"]
    min_margin, max_margin = config["profit_margin"]
    avg_discount = config["avg_discount"]

    shipping_modes = ["Standard Class", "Second Class", "First Class", "Same Day"]
    order_statuses = ["COMPLETE", "CLOSED", "PENDING", "PROCESSING", "ON_HOLD", "CANCELED"]

    # Pre-generate 150 customer profiles
    customers = []
    for c_idx in range(1, 151):
        cust_id = (tenant_id * 1000) + c_idx
        fname = fake.first_name()
        lname = fake.last_name()
        email = f"{fname.lower()}.{lname.lower()}{c_idx}@{config['name'].lower().replace(' ', '').replace('&', '')}.com"
        city = fake.city()
        state = fake.state()
        country = fake.country()
        zipcode = fake.postcode()
        street = fake.street_address()
        customers.append({
            "id": cust_id,
            "fname": fname,
            "lname": lname,
            "email": email,
            "city": city,
            "state": state,
            "country": country,
            "zipcode": zipcode,
            "street": street,
        })

    order_rows: List[Dict[str, Any]] = []
    shipping_rows: List[Dict[str, Any]] = []

    for i in range(1, target_rows + 1):
        order_id = 400000 + (tenant_id * 100000) + i
        item_id = 700000 + (tenant_id * 100000) + i
        cust = rng.choice(customers)

        category, product_name, price = rng.choice(catalog)
        qty = rng.randint(1, 5)

        # Discount rate tailored to tenant profile
        if config["shape"] == "high_discount_low_profit":
            discount_rate = round(rng.uniform(0.25, 0.40), 2)
        else:
            discount_rate = round(rng.choice([0.0, 0.05, 0.10, 0.15, 0.20]) if avg_discount > 0.05 else rng.choice([0.0, 0.0, 0.05]), 2)

        total = round(price * qty * (1.0 - discount_rate), 2)
        profit_ratio = round(rng.uniform(min_margin, max_margin), 2)
        profit = round(total * profit_ratio, 2)

        order_time = _sample_order_timestamp(shape, start_time, end_time, rng)

        # Scheduled shipping days and late delivery risk
        sched_days = rng.randint(2, 6)
        is_late = rng.random() < late_rate
        real_days = sched_days + (rng.randint(1, 4) if is_late else rng.randint(-1, 0))
        real_days = max(1, real_days)

        ship_time = order_time + timedelta(days=real_days)
        delivery_status = "Late delivery" if is_late else rng.choice(["Advance shipping", "Shipping on time"])

        # Base DataCo row
        row = {
            "Type": rng.choice(["DEBIT", "TRANSFER", "PAYMENT", "CASH"]),
            "Days for shipping (real)": real_days,
            "Days for shipment (scheduled)": sched_days,
            "Benefit per order": profit,
            "Sales per customer": total,
            "Delivery Status": delivery_status,
            "Late_delivery_risk": 1 if is_late else 0,
            "Category Id": hash(category) % 100 + 1,
            "Category Name": category,
            "Customer City": cust["city"],
            "Customer Country": cust["country"],
            "Customer Email": cust["email"],
            "Customer Fname": cust["fname"],
            "Customer Id": cust["id"],
            "Customer Lname": cust["lname"],
            "Customer Password": "********",
            "Customer Segment": "Consumer" if tenant_id % 2 == 0 else "Corporate",
            "Customer State": cust["state"],
            "Customer Street": cust["street"],
            "Customer Zipcode": cust["zipcode"],
            "Department Id": (tenant_id % 7) + 1,
            "Department Name": config["industry"],
            "Latitude": round(float(fake.latitude()), 4),
            "Longitude": round(float(fake.longitude()), 4),
            "Market": "Global",
            "Order City": cust["city"],
            "Order Country": cust["country"],
            "Order Customer Id": cust["id"],
            "order date (DateOrders)": order_time.strftime("%m/%d/%Y %H:%M"),
            "Order Id": order_id,
            "Order Item Cardprod Id": rng.randint(50, 800),
            "Order Item Discount": round(price * qty * discount_rate, 2),
            "Order Item Discount Rate": discount_rate,
            "Order Item Id": item_id,
            "Order Item Product Price": price,
            "Order Item Profit Ratio": profit_ratio,
            "Order Item Quantity": qty,
            "Sales": round(price * qty, 2),
            "Order Item Total": total,
            "Order Profit Per Order": profit,
            "Order Region": f"{cust['country']} North",
            "Order State": cust["state"],
            "Order Status": rng.choice(order_statuses),
            "Order Zipcode": cust["zipcode"],
            "Product Card Id": rng.randint(50, 800),
            "Product Category Id": hash(category) % 100 + 1,
            "Product Description": f"Helios Certified {product_name}",
            "Product Image": f"https://images.helios.io/products/{item_id}.jpg",
            "Product Name": product_name,
            "Product Price": price,
            "Product Status": 0,
            "shipping date (DateOrders)": ship_time.strftime("%m/%d/%Y %H:%M"),
            "Shipping Mode": rng.choice(shipping_modes),
        }

        order_rows.append(row)
        shipping_rows.append(dict(row))

    return order_rows, shipping_rows


def _rename_excel_headers(
    rows: List[Dict[str, Any]],
    mapping: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Rename selected dictionary keys to fuzzy variants and return new column order."""
    renamed_rows: List[Dict[str, Any]] = []
    for r in rows:
        new_row = {}
        for k, v in r.items():
            renamed_key = mapping.get(k, k)
            new_row[renamed_key] = v
        renamed_rows.append(new_row)

    # Reconstruct headers preserving order with renamed variants
    new_headers = [mapping.get(c, c) for c in DATACO_COLUMNS]
    return renamed_rows, new_headers


def _write_excel(
    file_path: Path,
    rows: List[Dict[str, Any]],
    headers: List[str],
) -> None:
    """Save rows into an Excel .xlsx workbook with openpyxl."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(headers)

    for r in rows:
        row_vals = [r.get(col, "") for col in headers]
        ws.append(row_vals)

    wb.save(str(file_path))


def generate_synthetic_tenants(
    output_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Generate synthetic datasets for Tenants 4-10.
    Outputs .xlsx for tenants 4-5 and .csv for tenants 6-10.
    Returns summary metadata records for reporting.
    """
    if output_dir is None:
        output_dir = get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Date range: end within last 7 days, span 9 months (270 days)
    start_time, end_time = generate_date_range(span_days=270, end_days_ago=3)
    logger.info("Generating synthetic data for Tenants 4-10 spanning %s to %s", start_time.date(), end_time.date())

    summary_records: List[Dict[str, Any]] = []

    for config in SYNTHETIC_TENANT_CONFIGS:
        tenant_id = config["tenant_id"]
        logger.info("Generating Tenant %d (%s) - Target: %d rows [%s]...", tenant_id, config["name"], config["target_rows"], config["format"])

        # 1. Base generation
        order_rows, shipping_rows = generate_tenant_records(config, start_time, end_time)

        # 2. Inject deliberate bad rows (~3%)
        corrupted_orders, bad_orders_count = inject_bad_rows(
            order_rows,
            bad_ratio=0.03,
            seed=config["seed"] + 1,
        )
        corrupted_shipping, bad_shipping_count = inject_bad_rows(
            shipping_rows,
            bad_ratio=0.03,
            seed=config["seed"] + 2,
        )

        date_range_str = extract_date_range(corrupted_orders)

        # 3. Output files based on format
        if config["format"] == "xlsx":
            # Apply fuzzy header renames for Excel demonstration
            final_orders, orders_headers = _rename_excel_headers(corrupted_orders, EXCEL_ORDERS_HEADER_MAP)
            final_shipping, shipping_headers = _rename_excel_headers(corrupted_shipping, EXCEL_SHIPPING_HEADER_MAP)

            orders_file = output_dir / config["orders_file"]
            shipping_file = output_dir / config["shipping_file"]

            _write_excel(orders_file, final_orders, orders_headers)
            _write_excel(shipping_file, final_shipping, shipping_headers)

        else:
            # Standard CSV format
            orders_file = output_dir / config["orders_file"]
            shipping_file = output_dir / config["shipping_file"]

            with open(orders_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=DATACO_COLUMNS, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(corrupted_orders)

            with open(shipping_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=DATACO_COLUMNS, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(corrupted_shipping)

        # Record summary metrics
        summary_records.append({
            "tenant": tenant_id,
            "file_name": config["orders_file"],
            "row_count": len(corrupted_orders),
            "date_range": date_range_str,
            "bad_rows": bad_orders_count,
        })
        summary_records.append({
            "tenant": tenant_id,
            "file_name": config["shipping_file"],
            "row_count": len(corrupted_shipping),
            "date_range": date_range_str,
            "bad_rows": bad_shipping_count,
        })

        logger.info(
            "Tenant %d completed: %s (%d rows, %d bad), %s (%d rows, %d bad)",
            tenant_id,
            config["orders_file"],
            len(corrupted_orders),
            bad_orders_count,
            config["shipping_file"],
            len(corrupted_shipping),
            bad_shipping_count,
        )

    return summary_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic tenant demo datasets (Tenants 4-10)")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="Target output directory (default: scripts/output/)",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else get_output_dir()
    summary = generate_synthetic_tenants(output_dir=out_dir)
    print_summary_table(summary)


if __name__ == "__main__":
    main()
