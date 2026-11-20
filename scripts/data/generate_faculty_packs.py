#!/usr/bin/env python3
"""
Generate Faculty Demonstration Packs for live evaluation and viva testing.
Output directory: scripts/data/faculty_packs/

Features:
- Fixed random seed (2026) for deterministic generation.
- Standard 13-column orders format and 6-column shipping format.
- Amounts in INR (₹).
- Generates clean packs: clean_10_orders.csv, clean_50_orders.csv, clean_50_orders.xlsx (and matching shipping files).
- Generates 14 specialized test files testing exact error types and edge cases with known expected counts.
"""

import csv
import datetime as dt
import os
import random
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import openpyxl

# Set fixed seed for deterministic reproducibility
random.seed(2026)

OUTPUT_DIR = Path(__file__).resolve().parent / "faculty_packs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

Q = lambda x: Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

ORDER_HEADERS = [
    "order_id", "order_date", "customer_id", "customer_name", "segment",
    "product_id", "product_name", "category", "quantity", "unit_price",
    "discount", "total", "profit"
]

SHIPPING_HEADERS = [
    "order_id", "shipping_mode", "delivery_status",
    "scheduled_date", "actual_date", "shipping_days"
]

PRODUCT_CATALOG = [
    ("P-FAC-01", "Handloom Silk Saree", "Ethnic Wear", 3499.00, 0.32),
    ("P-FAC-02", "Block Print Cotton Kurta", "Ethnic Wear", 999.00, 0.28),
    ("P-FAC-03", "Wireless Ergonomic Mouse", "Electronics", 799.00, 0.22),
    ("P-FAC-04", "Ayurvedic Face Oil", "Beauty & Wellness", 449.00, 0.40),
    ("P-FAC-05", "Hardcover Research Journal", "Stationery", 299.00, 0.35),
    ("P-FAC-06", "Organic Assam Tea 500g", "Groceries", 399.00, 0.25),
    ("P-FAC-07", "Leather Laptop Briefcase", "Accessories", 2499.00, 0.30),
    ("P-FAC-08", "Ceramic Artisan Coffee Mug", "Home & Kitchen", 349.00, 0.30),
]

CUSTOMERS = [
    ("C-FAC-001", "Dr. Alok Verma", "Consumer"),
    ("C-FAC-002", "Pooja Deshmukh", "Corporate"),
    ("C-FAC-003", "Vikramaditya Iyer", "Consumer"),
    ("C-FAC-004", "Meera Sundaram", "Home Office"),
    ("C-FAC-005", "Prof. Sneha Patel", "Consumer"),
    ("C-FAC-006", "Rohan Bhattacharya", "Corporate"),
    ("C-FAC-007", "Ananya Kulkarni", "Consumer"),
    ("C-FAC-008", "Manish Malhotra", "Home Office"),
]

SHIPPING_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]


def generate_clean_row(order_num: int, base_date: dt.date = dt.date(2026, 8, 1)) -> tuple[dict, dict]:
    """Generate a single clean matching order and shipping row."""
    order_id = f"ORD-FAC-{order_num:05d}"
    order_date = base_date + dt.timedelta(days=(order_num % 60))
    cust_id, cust_name, segment = random.choice(CUSTOMERS)
    prod_id, prod_name, category, unit_price, margin = random.choice(PRODUCT_CATALOG)
    qty = random.randint(1, 4)
    disc_rate = random.choice([0.0, 0.05, 0.10, 0.15])
    
    subtotal = Q(unit_price * qty)
    discount = Q(subtotal * Decimal(str(disc_rate)))
    total = Q(subtotal - discount)
    profit = Q(total * Decimal(str(margin)))

    shipping_mode = random.choice(SHIPPING_MODES)
    days_to_ship = {"Same Day": 0, "First Class": 2, "Second Class": 3, "Standard Class": 5}[shipping_mode]
    scheduled_date = order_date + dt.timedelta(days=days_to_ship)
    is_late = random.random() < 0.15
    actual_days = days_to_ship + (2 if is_late else 0)
    actual_date = order_date + dt.timedelta(days=actual_days)
    status = "Late" if is_late else "On Time"

    order_row = {
        "order_id": order_id,
        "order_date": order_date.strftime("%Y-%m-%d"),
        "customer_id": cust_id,
        "customer_name": cust_name,
        "segment": segment,
        "product_id": prod_id,
        "product_name": prod_name,
        "category": category,
        "quantity": qty,
        "unit_price": f"{unit_price:.2f}",
        "discount": f"{discount:.2f}",
        "total": f"{total:.2f}",
        "profit": f"{profit:.2f}",
    }

    shipping_row = {
        "order_id": order_id,
        "shipping_mode": shipping_mode,
        "delivery_status": status,
        "scheduled_date": scheduled_date.strftime("%Y-%m-%d"),
        "actual_date": actual_date.strftime("%Y-%m-%d"),
        "shipping_days": actual_days,
    }

    return order_row, shipping_row


def write_csv(path: Path, headers: list[str], rows: list[dict]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, headers: list[str], rows: list[dict]):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])
    wb.save(path)


def generate_all_packs():
    print(f"Generating Faculty Demonstration Packs in: {OUTPUT_DIR}")

    # 1. clean_10_orders.csv & clean_10_shipping.csv
    c10_orders, c10_shipping = [], []
    for i in range(1, 11):
        o, s = generate_clean_row(i)
        c10_orders.append(o)
        c10_shipping.append(s)
    write_csv(OUTPUT_DIR / "clean_10_orders.csv", ORDER_HEADERS, c10_orders)
    write_csv(OUTPUT_DIR / "clean_10_shipping.csv", SHIPPING_HEADERS, c10_shipping)
    print("  ✓ clean_10_orders.csv & clean_10_shipping.csv (10 rows)")

    # 2. clean_50_orders.csv & clean_50_shipping.csv
    c50_orders, c50_shipping = [], []
    for i in range(1, 51):
        o, s = generate_clean_row(i)
        c50_orders.append(o)
        c50_shipping.append(s)
    write_csv(OUTPUT_DIR / "clean_50_orders.csv", ORDER_HEADERS, c50_orders)
    write_csv(OUTPUT_DIR / "clean_50_shipping.csv", SHIPPING_HEADERS, c50_shipping)
    print("  ✓ clean_50_orders.csv & clean_50_shipping.csv (50 rows)")

    # 3. clean_50_orders.xlsx & clean_50_shipping.xlsx
    write_xlsx(OUTPUT_DIR / "clean_50_orders.xlsx", ORDER_HEADERS, c50_orders)
    write_xlsx(OUTPUT_DIR / "clean_50_shipping.xlsx", SHIPPING_HEADERS, c50_shipping)
    print("  ✓ clean_50_orders.xlsx & clean_50_shipping.xlsx (50 rows)")

    # Helper to generate a 15-row baseline for error packs
    def base_15():
        ords, ships = [], []
        for i in range(1, 16):
            o, s = generate_clean_row(i)
            ords.append(o)
            ships.append(s)
        return ords, ships

    # 4. err01_blank_quantity: 15 rows, 3 bad rows (rows 3, 7, 11 have blank quantity)
    ords, ships = base_15()
    for idx in (2, 6, 10):
        ords[idx]["quantity"] = ""
    write_csv(OUTPUT_DIR / "err01_blank_quantity_orders.csv", ORDER_HEADERS, ords)
    write_csv(OUTPUT_DIR / "err01_blank_quantity_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err01_blank_quantity (15 rows: 12 valid, 3 blank quantity)")

    # 5. err02_negative_quantity: 15 rows, 3 bad rows (rows 3, 7, 11 have negative qty)
    ords, ships = base_15()
    ords[2]["quantity"] = -1
    ords[6]["quantity"] = -2
    ords[10]["quantity"] = -5
    write_csv(OUTPUT_DIR / "err02_negative_quantity_orders.csv", ORDER_HEADERS, ords)
    write_csv(OUTPUT_DIR / "err02_negative_quantity_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err02_negative_quantity (15 rows: 12 valid, 3 negative quantity)")

    # 6. err03_zero_or_negative_price: 15 rows, 3 bad rows (rows 3, 7, 11 have zero or neg price)
    ords, ships = base_15()
    ords[2]["unit_price"] = "0.00"
    ords[6]["unit_price"] = "-499.00"
    ords[10]["unit_price"] = "0"
    write_csv(OUTPUT_DIR / "err03_zero_or_negative_price_orders.csv", ORDER_HEADERS, ords)
    write_csv(OUTPUT_DIR / "err03_zero_or_negative_price_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err03_zero_or_negative_price (15 rows: 12 valid, 3 zero/negative price)")

    # 7. err04_unreadable_date: 15 rows, 3 bad rows (rows 3, 7, 11 have unreadable date)
    ords, ships = base_15()
    ords[2]["order_date"] = "not-a-valid-date"
    ords[6]["order_date"] = "32/13/2026"
    ords[10]["order_date"] = "unreadable_text"
    write_csv(OUTPUT_DIR / "err04_unreadable_date_orders.csv", ORDER_HEADERS, ords)
    write_csv(OUTPUT_DIR / "err04_unreadable_date_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err04_unreadable_date (15 rows: 12 valid, 3 unreadable date)")

    # 8. err05_mixed_date_formats: 15 rows, 0 bad rows (8 YYYY-MM-DD, 7 DD/MM/YYYY, both parseable)
    ords, ships = base_15()
    for idx in (1, 3, 5, 7, 9, 11, 13):
        # convert YYYY-MM-DD to unambiguous DD/MM/YYYY
        d = dt.datetime.strptime(ords[idx]["order_date"], "%Y-%m-%d").date()
        ords[idx]["order_date"] = d.strftime("%d/%m/%Y")
    write_csv(OUTPUT_DIR / "err05_mixed_date_formats_orders.csv", ORDER_HEADERS, ords)
    write_csv(OUTPUT_DIR / "err05_mixed_date_formats_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err05_mixed_date_formats (15 rows: 15 valid, 0 bad rows, mixed parseable dates)")

    # 9. err06_duplicate_order_ids: 15 rows, 3 bad rows (rows 4, 8, 12 repeat rows 1, 5, 9)
    ords, ships = base_15()
    ords[3] = dict(ords[0])
    ords[7] = dict(ords[4])
    ords[11] = dict(ords[8])
    write_csv(OUTPUT_DIR / "err06_duplicate_order_ids_orders.csv", ORDER_HEADERS, ords)
    write_csv(OUTPUT_DIR / "err06_duplicate_order_ids_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err06_duplicate_order_ids (15 rows: 12 unique, 3 duplicate lines)")

    # 10. err07_missing_customer_id: 15 rows, 3 bad rows (rows 3, 7, 11 have empty customer_id)
    ords, ships = base_15()
    ords[2]["customer_id"] = ""
    ords[6]["customer_id"] = ""
    ords[10]["customer_id"] = ""
    write_csv(OUTPUT_DIR / "err07_missing_customer_id_orders.csv", ORDER_HEADERS, ords)
    write_csv(OUTPUT_DIR / "err07_missing_customer_id_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err07_missing_customer_id (15 rows: 12 valid, 3 missing customer_id)")

    # 11. err08_arithmetic_mismatch: 15 rows, 3 bad rows (rows 3, 7, 11 have total != qty * price - disc)
    ords, ships = base_15()
    ords[2]["total"] = "9999.00"
    ords[6]["total"] = "50000.00"
    ords[10]["total"] = "1.00"
    write_csv(OUTPUT_DIR / "err08_arithmetic_mismatch_orders.csv", ORDER_HEADERS, ords)
    write_csv(OUTPUT_DIR / "err08_arithmetic_mismatch_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err08_arithmetic_mismatch (15 rows: 12 valid, 3 arithmetic mismatch)")

    # 12. err09_currency_text_formats: 15 rows (12 rows with varied Indian currency text strings, 3 bad unparseable)
    ords, ships = base_15()
    # Apply valid Indian currency text formats to 12 rows
    # Recalculate total cleanly and format both unit_price and total
    currency_patterns = [
        "₹1,25,000.00", "Rs. 1,250", "Rs 1250", "INR 899", "1250/-",
        "₹ 2,499.00", "Rs. 3,499.00", "INR 1,199", "799/-", "₹ 999.00",
        "Rs 1599", "INR 699"
    ]
    for i in range(12):
        row = ords[i]
        # set clean values with currency strings
        q = int(row["quantity"])
        p = Decimal("1250.00") if i % 2 == 0 else Decimal("899.00")
        d = Decimal("0.00")
        t = q * p - d
        row["unit_price"] = "Rs. 1,250" if p == 1250 else "INR 899"
        row["discount"] = "0.00"
        row["total"] = f"₹{t:,.2f}" if i % 2 == 0 else f"{t}/-"
    # Add 3 unparseable currency rows at the end (rows 13, 14, 15)
    ords[12]["unit_price"] = "Rs. INVALID_PRICE"
    ords[13]["total"] = "INR N/A"
    ords[14]["unit_price"] = "₹---"
    write_csv(OUTPUT_DIR / "err09_currency_text_formats_orders.csv", ORDER_HEADERS, ords)
    write_csv(OUTPUT_DIR / "err09_currency_text_formats_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err09_currency_text_formats (15 rows: 12 valid currency text strings, 3 unparseable)")

    # 13. err10_renamed_headers: 15 rows, 0 bad rows (aliases matched during schema inference)
    ords, ships = base_15()
    renamed_headers = [
        "order_number", "order_date", "cust_id", "cust_name", "market_segment",
        "product_id", "item_name", "category", "qty", "price",
        "discount", "total_amt", "profit"
    ]
    renamed_rows = []
    for r in ords:
        renamed_rows.append({
            "order_number": r["order_id"],
            "order_date": r["order_date"],
            "cust_id": r["customer_id"],
            "cust_name": r["customer_name"],
            "market_segment": r["segment"],
            "product_id": r["product_id"],
            "item_name": r["product_name"],
            "category": r["category"],
            "qty": r["quantity"],
            "price": r["unit_price"],
            "discount": r["discount"],
            "total_amt": r["total"],
            "profit": r["profit"],
        })
    write_csv(OUTPUT_DIR / "err10_renamed_headers_orders.csv", renamed_headers, renamed_rows)
    write_csv(OUTPUT_DIR / "err10_renamed_headers_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err10_renamed_headers (15 rows: 15 valid, 0 bad rows, aliased headers matched by schema inference)")

    # 14. err11_extra_unknown_columns: 15 rows, 0 bad rows (extra columns ignored)
    ords, ships = base_15()
    extra_headers = ORDER_HEADERS + ["warehouse_code", "special_delivery_notes"]
    for r in ords:
        r["warehouse_code"] = "WH-AHMEDABAD-01"
        r["special_delivery_notes"] = "Handle with care, call customer on delivery"
    write_csv(OUTPUT_DIR / "err11_extra_unknown_columns_orders.csv", extra_headers, ords)
    write_csv(OUTPUT_DIR / "err11_extra_unknown_columns_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err11_extra_unknown_columns (15 rows: 15 valid, 0 bad rows, unknown columns safely ignored)")

    # 15. err12_missing_required_column: 15 rows, 15 bad rows (customer_id column completely missing)
    ords, ships = base_15()
    missing_headers = [h for h in ORDER_HEADERS if h != "customer_id"]
    missing_rows = [{k: v for k, v in r.items() if k != "customer_id"} for r in ords]
    write_csv(OUTPUT_DIR / "err12_missing_required_column_orders.csv", missing_headers, missing_rows)
    write_csv(OUTPUT_DIR / "err12_missing_required_column_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err12_missing_required_column (15 rows: 0 valid, 15 rejected for missing customer_id)")

    # 16. err13_text_spaces_and_casing: 15 rows, 0 bad rows (whitespace stripped, mixed case accepted)
    ords, ships = base_15()
    for r in ords:
        r["order_id"] = f"   {r['order_id']}   "
        r["customer_name"] = f"  {r['customer_name'].swapcase()}  "
        r["segment"] = f"  {r['segment'].upper()}  "
        r["product_name"] = f"  {r['product_name']}  "
        r["category"] = f"  {r['category'].lower()}  "
    write_csv(OUTPUT_DIR / "err13_text_spaces_and_casing_orders.csv", ORDER_HEADERS, ords)
    write_csv(OUTPUT_DIR / "err13_text_spaces_and_casing_shipping.csv", SHIPPING_HEADERS, ships)
    print("  ✓ err13_text_spaces_and_casing (15 rows: 15 valid, 0 bad rows, whitespace & casing normalized)")

    # 17. err14_header_only: 0 data rows (caught at upload validation boundary)
    write_csv(OUTPUT_DIR / "err14_header_only_orders.csv", ORDER_HEADERS, [])
    print("  ✓ err14_header_only (0 rows: rejected at upload boundary with HTTP 400)")

    print(f"\nAll Faculty Demonstration Packs generated successfully in {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_all_packs()

