#!/usr/bin/env python3
"""
Helios Data Platform - Shared Demo Data Preparation Helpers

Provides shared utilities for:
- Deterministic random seed management
- Canonical DataCo column definitions & schema representations
- Date range generation anchored within the last 7 days (spanning 6-12 months)
- Deliberate bad-row injection (~3% of rows) across 5 defect types
- Output folder resolution (scripts/output/)
- Formatted summary table reporting
"""

import csv
import logging
import os
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

logger = logging.getLogger("helios.data.common")

# Default deterministic seed
DEFAULT_SEED = 42

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


def get_output_dir() -> Path:
    """Return the resolved scripts/output directory, creating it if needed."""
    # scripts/data/ -> scripts/output/
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def set_random_seed(seed: int = DEFAULT_SEED) -> None:
    """Set seeds for standard random and Faker (if installed)."""
    random.seed(seed)
    try:
        from faker import Faker
        Faker.seed(seed)
    except ImportError:
        pass


def generate_date_range(
    span_days: int = 270,
    end_days_ago: int = 3,
    ref_date: Optional[datetime] = None,
) -> Tuple[datetime, datetime]:
    """
    Generate start and end datetimes.
    - End date falls within the last 7 days before today (ref_date).
    - Start date spans 6 to 12 months prior (180 - 365 days).
    """
    if ref_date is None:
        ref_date = datetime.now(timezone.utc)
    elif ref_date.tzinfo is None:
        ref_date = ref_date.replace(tzinfo=timezone.utc)

    # Ensure end_days_ago is within [1, 6]
    end_days = max(1, min(6, end_days_ago))
    end_time = ref_date - timedelta(days=end_days, hours=random.randint(1, 12))
    start_time = end_time - timedelta(days=max(180, min(365, span_days)))

    return start_time, end_time


def inject_bad_rows(
    rows: List[Dict[str, Any]],
    bad_ratio: float = 0.03,
    seed: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Deliberately inject ~3% corrupted rows into a dataset.
    Corruptions spread across:
      1. Null quantities (empty string or None)
      2. Duplicate order lines (duplicated record with matching order & item IDs)
      3. Mixed date formats (DD/MM/YYYY and YYYY-MM-DD in the same file)
      4. Currency symbols and thousands separators in price columns ("$1,250.00")
      5. Negative quantities (-1, -2, -5)

    Returns:
        (corrupted_rows, total_bad_rows_count)
    """
    if not rows:
        return rows, 0

    rng = random.Random(seed if seed is not None else DEFAULT_SEED)
    total_rows = len(rows)
    target_bad_count = max(1, int(round(total_rows * bad_ratio)))

    # Work on a shallow copy of dictionaries
    corrupted_rows = [dict(r) for r in rows]

    # Partition the target bad count into 5 defect categories
    bucket_size = target_bad_count // 5
    remainder = target_bad_count % 5

    counts = [
        bucket_size + (1 if 0 < remainder else 0),  # null quantities
        bucket_size + (1 if 1 < remainder else 0),  # duplicate lines
        bucket_size + (1 if 2 < remainder else 0),  # mixed date formats
        bucket_size + (1 if 3 < remainder else 0),  # currency format in price
        bucket_size,                                # negative quantities
    ]

    # Select random unique candidate indices for non-duplicate corruptions
    non_dupe_needed = counts[0] + counts[2] + counts[3] + counts[4]
    candidate_indices = rng.sample(range(total_rows), min(non_dupe_needed, total_rows))

    idx_ptr = 0

    # 1. Null quantities
    null_qty_indices = candidate_indices[idx_ptr : idx_ptr + counts[0]]
    idx_ptr += counts[0]
    for idx in null_qty_indices:
        row = corrupted_rows[idx]
        for key in ["Order Item Quantity", "Qty", "quantity", "Quantity"]:
            if key in row:
                row[key] = ""  # blank/null
                break

    # 2. Mixed date formats (DD/MM/YYYY and YYYY-MM-DD)
    date_indices = candidate_indices[idx_ptr : idx_ptr + counts[2]]
    idx_ptr += counts[2]
    for i, idx in enumerate(date_indices):
        row = corrupted_rows[idx]
        for date_key in [
            "order date (DateOrders)",
            "Order_Dt",
            "order_date",
            "shipping date (DateOrders)",
            "Ship_Date",
            "shipped_at",
        ]:
            if date_key in row and row[date_key]:
                raw_val = str(row[date_key])
                # Try to parse existing date to reformat
                parsed_dt = None
                for fmt in ["%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"]:
                    try:
                        parsed_dt = datetime.strptime(raw_val.split(".")[0], fmt)
                        break
                    except ValueError:
                        continue

                if not parsed_dt:
                    parsed_dt = datetime(2026, 3, 15, 10, 30)

                # Alternate between DD/MM/YYYY and YYYY-MM-DD
                if i % 2 == 0:
                    row[date_key] = parsed_dt.strftime("%d/%m/%Y")
                else:
                    row[date_key] = parsed_dt.strftime("%Y-%m-%d")
                break

    # 3. Currency symbols and thousands separators in price columns ("$1,250.00")
    currency_indices = candidate_indices[idx_ptr : idx_ptr + counts[3]]
    idx_ptr += counts[3]
    for idx in currency_indices:
        row = corrupted_rows[idx]
        for price_key in [
            "Sales",
            "Order Item Total",
            "Order Item Product Price",
            "Product Price",
            "Total_Amount",
            "Unit_Price",
            "total",
            "unit_price",
        ]:
            if price_key in row and row[price_key] not in (None, ""):
                try:
                    val = float(str(row[price_key]).replace("$", "").replace(",", ""))
                except ValueError:
                    val = 1250.00
                row[price_key] = f"${val:,.2f}"
                break

    # 4. Negative quantities
    neg_qty_indices = candidate_indices[idx_ptr : idx_ptr + counts[4]]
    for idx in neg_qty_indices:
        row = corrupted_rows[idx]
        neg_val = rng.choice([-1, -2, -5])
        for key in ["Order Item Quantity", "Qty", "quantity", "Quantity"]:
            if key in row:
                row[key] = neg_val
                break

    # 5. Duplicate order lines (take sample from existing rows and insert duplicates)
    dupe_count = counts[1]
    if dupe_count > 0:
        dupe_sources = rng.sample(corrupted_rows, min(dupe_count, len(corrupted_rows)))
        for src in dupe_sources:
            dupe_row = dict(src)
            # Insert duplicate adjacent or at end
            corrupted_rows.append(dupe_row)

    total_injected = sum(counts)
    return corrupted_rows, total_injected


def extract_date_range(rows: Sequence[Dict[str, Any]]) -> str:
    """Extract and format min and max dates found across rows."""
    if not rows:
        return "N/A"

    date_keys = [
        "order date (DateOrders)",
        "Order_Dt",
        "order_date",
        "shipping date (DateOrders)",
        "Ship_Date",
        "shipped_at",
    ]

    dates: List[datetime] = []
    for r in rows:
        for k in date_keys:
            val = r.get(k)
            if val:
                raw_str = str(val).strip()
                for fmt in [
                    "%m/%d/%Y %H:%M",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%m/%d/%Y",
                    "%Y/%m/%d",
                ]:
                    try:
                        parsed = datetime.strptime(raw_str.split(".")[0], fmt)
                        dates.append(parsed)
                        break
                    except ValueError:
                        continue
                if dates and len(dates) >= len(rows):
                    break

    if not dates:
        return "N/A"

    min_date = min(dates)
    max_date = max(dates)
    return f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"


def print_summary_table(summary_records: List[Dict[str, Any]]) -> None:
    """
    Print an aligned summary table of generated tenant files.
    Expected keys per record:
      - tenant: int or str (e.g. 1)
      - file_name: str (e.g. 'tenant_1_orders.csv')
      - row_count: int (e.g. 12500)
      - date_range: str (e.g. '2025-10-15 to 2026-10-04')
      - bad_rows: int (e.g. 0 or 375)
    """
    headers = ["Tenant", "File Name", "Row Count", "Date Range", "Bad Rows"]

    rows = []
    for rec in summary_records:
        rows.append([
            f"Tenant {rec.get('tenant', '')}",
            str(rec.get("file_name", "")),
            f"{int(rec.get('row_count', 0)):,}",
            str(rec.get("date_range", "N/A")),
            f"{int(rec.get('bad_rows', 0)):,}",
        ])

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    # Padding
    col_widths = [w + 2 for w in col_widths]

    sep_line = "+" + "+".join("-" * w for w in col_widths) + "+"
    header_line = "|" + "|".join(f" {h}".ljust(col_widths[i]) for i, h in enumerate(headers)) + "|"

    print("\n" + "=" * len(sep_line))
    print(" HELIOS DEMO DATA GENERATION SUMMARY TABLE ".center(len(sep_line)))
    print("=" * len(sep_line))
    print(sep_line)
    print(header_line)
    print(sep_line)

    for row in rows:
        line = "|" + "|".join(f" {cell}".ljust(col_widths[i]) for i, cell in enumerate(row)) + "|"
        print(line)

    print(sep_line + "\n")
