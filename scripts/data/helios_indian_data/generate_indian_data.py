#!/usr/bin/env python3
"""Generate complete Indian-rupee demo data for the 10 Helios organizations.

Usage:  python generate_indian_data.py [--scale 1.0] [--out helios_indian_data]
Produces, per organization: orders (CSV, or XLSX for orgs 3 and 6) and shipping CSV,
plus manifest.csv and expected_totals.json (numbers to compare against the dashboards).
Amounts are plain numbers in rupees. A fixed seed makes every run identical.
"""
import argparse, csv, datetime as dt, json, os, random
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

import openpyxl

ap = argparse.ArgumentParser()
ap.add_argument("--scale", type=float, default=1.0, help="multiply order counts (use 0.4 for a quick test)")
ap.add_argument("--out", default="helios_indian_data")
args = ap.parse_args()
random.seed(2026)
Q = lambda x: Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

START, END = dt.date(2026, 7, 1), dt.date(2026, 10, 19)
DAYS = [START + dt.timedelta(days=i) for i in range((END - START).days + 1)]

FIRST = ["Aarav","Vivaan","Aditya","Arjun","Rohan","Karan","Vikram","Rahul","Amit","Sanjay",
         "Ananya","Diya","Priya","Sneha","Kavya","Neha","Pooja","Isha","Meera","Riya",
         "Harsh","Nikhil","Siddharth","Manish","Deepak","Anjali","Shreya","Tanvi","Divya","Swati"]
LAST = ["Sharma","Patel","Iyer","Nair","Reddy","Mehta","Shah","Singh","Gupta","Joshi",
        "Kulkarni","Deshmukh","Bhatt","Menon","Chopra","Verma","Desai","Pillai","Rao","Malhotra"]

# org id: name, industry, orders, trend, margin, late rate, bad rows, max qty, catalog
C = {
 1: ("Kaveri Textiles & Crafts","Apparel",260,"seasonal",0.30,0.18,6,3,[
     ("Cotton Kurta","Ethnic Wear",799),("Silk Saree","Ethnic Wear",4999),("Handloom Dupatta","Ethnic Wear",1299),
     ("Block Print Shirt","Menswear",1199),("Linen Trousers","Menswear",1599),("Embroidered Kurti","Womenswear",999),
     ("Kids Cotton Set","Kidswear",699),("Cotton Stole","Accessories",549)]),
 2: ("Sahyadri Infotech Solutions","Electronics",230,"stable",0.18,0.14,0,3,[
     ("Wireless Earbuds","Audio",1999),("Bluetooth Speaker","Audio",2499),("Power Bank 20000mAh","Mobile Accessories",1799),
     ("USB-C Cable","Mobile Accessories",399),("Smart Watch","Wearables",4499),("HD Webcam","Computer Accessories",2299),
     ("Wireless Mouse","Computer Accessories",799),("Wi-Fi 6 Router","Networking",3999)]),
 3: ("Vanguard Home Office","Home & Office",200,"stable",0.28,0.15,0,2,[
     ("Ergonomic Office Chair","Furniture",8999),("Study Desk","Furniture",6499),("LED Desk Lamp","Lighting",1299),
     ("Monitor Stand","Accessories",1499),("Filing Cabinet","Storage",5499),("Whiteboard","Stationery",1899),
     ("Notebook Set","Stationery",349),("Cable Organizer","Accessories",299)]),
 4: ("Velvet Botanicals","Beauty",250,"growing",0.45,0.12,6,4,[
     ("Herbal Face Wash","Skincare",249),("Aloe Vera Gel","Skincare",299),("Amla Hair Oil","Haircare",349),
     ("Vitamin C Serum","Skincare",799),("Kajal","Makeup",199),("Sandalwood Soap Pack","Bath & Body",399),
     ("Lip Balm","Makeup",149),("Body Lotion","Bath & Body",449)]),
 5: ("Summit Peak Athletics","Sports",190,"seasonal",0.27,0.17,0,3,[
     ("Yoga Mat","Fitness",899),("Dumbbell Set","Fitness",2499),("Cricket Bat","Cricket",2999),
     ("Cricket Ball Pack","Cricket",599),("Running Shoes","Footwear",3499),("Badminton Racket","Racket Sports",1799),
     ("Skipping Rope","Fitness",249),("Sports Water Bottle","Accessories",449)]),
 6: ("Page & Quill Publishing","Books",210,"stable",0.35,0.10,0,4,[
     ("Hardcover Novel","Fiction",499),("Children's Story Set","Kids",699),("Competitive Exam Guide","Education",899),
     ("Cookbook","Lifestyle",599),("Biography","Non-Fiction",399),("Comic Collection","Comics",799),
     ("Dictionary","Reference",449),("Journal Notebook","Stationery",299)]),
 7: ("WonderKite Toyworks","Toys",180,"declining",0.25,0.42,8,3,[
     ("Wooden Building Blocks","Learning",899),("Remote Control Car","Vehicles",1499),("Family Board Game","Games",799),
     ("Large Soft Toy","Soft Toys",999),("500-Piece Puzzle","Puzzles",499),("Kite and Manja Set","Outdoor",349),
     ("Art and Craft Kit","Creative",649),("Educational Robot Kit","STEM",2499)]),
 8: ("Terra Verde Organics","Grocery",300,"stable",0.12,0.16,0,6,[
     ("Basmati Rice 5kg","Staples",549),("Groundnut Oil 1L","Oils",349),("Organic Toor Dal 1kg","Pulses",189),
     ("Whole Wheat Atta 5kg","Staples",299),("Masala Chai 250g","Beverages",179),("Jaggery 1kg","Staples",119),
     ("Mixed Dry Fruits 500g","Snacks",699),("Turmeric Powder 200g","Spices",99)]),
 9: ("Luminary Fine Gems","Jewellery",120,"seasonal",0.30,0.20,0,2,[
     ("Silver Anklet Pair","Silver",2499),("Gold-Plated Earrings","Fashion",1999),("Kundan Necklace Set","Bridal",6999),
     ("Pearl Studs","Fashion",1499),("Temple Jewellery Haram","Bridal",12999),("Silver Ring","Silver",1299),
     ("Bangle Set","Fashion",899),("Mangalsutra","Bridal",8499)]),
 10: ("Paws & Trails Outfitters","Pet Supplies",170,"growing",0.32,0.13,0,3,[
     ("Dog Food 3kg","Dog Care",899),("Cat Litter 5kg","Cat Care",499),("Pet Leash","Dog Care",399),
     ("Chew Toy Pack","Dog Care",349),("Pet Bed Medium","Comfort",1799),("Cat Scratcher","Cat Care",1299),
     ("Pet Shampoo","Grooming",349),("Travel Bowl","Accessories",299)]),
}

def day_weights(trend):
    n = len(DAYS); w = []
    for i, d in enumerate(DAYS):
        x = 1.0
        if trend == "growing":   x = 0.6 + 1.0 * i / (n - 1)
        if trend == "declining": x = 1.6 - 1.1 * i / (n - 1)
        if trend == "seasonal" and dt.date(2026, 10, 5) <= d <= dt.date(2026, 10, 19): x = 2.2
        if d.weekday() >= 5: x *= 1.25
        w.append(x)
    return w

MODES = [("Standard Class", 5, 0.45), ("Second Class", 3, 0.25), ("First Class", 2, 0.20), ("Same Day", 1, 0.10)]
HEADER = ["order_id","order_date","customer_id","customer_name","segment","product_id",
          "product_name","category","quantity","unit_price","discount","total","profit"]
SHIP_HEADER = ["order_id","shipping_mode","delivery_status","scheduled_date","actual_date","shipping_days"]

os.makedirs(args.out, exist_ok=True)
manifest, expected = [], {}

for oid, (name, industry, n0, trend, margin, late_rate, nbad, maxq, cat) in C.items():
    n = max(20, int(n0 * args.scale))
    customers = []
    for k in range(30):
        seg = random.choices(["Consumer","Corporate","Home Office"], [0.65, 0.20, 0.15])[0]
        customers.append((f"C{oid:02d}{k+1:03d}", f"{random.choice(FIRST)} {random.choice(LAST)}", seg))
    products = [(f"P{oid:02d}{k+1:02d}", nm, ct, pr) for k, (nm, ct, pr) in enumerate(cat)]
    weights = day_weights(trend)
    dates = sorted(random.choices(DAYS, weights, k=n))
    rows, ship = [], []
    for i, d in enumerate(dates, 1):
        cid, cname, seg = random.choice(customers)
        pid, pname, pcat, price = random.choices(products, [3,2,2,2,2,2,2,2] if industry != "Jewellery" else [2,2,1,2,1,2,2,1])[0]
        qty = random.randint(1, maxq)
        gross = Q(qty * price)
        disc = Q(gross * Decimal(str(random.choice([0, 0, 0, 0.05, 0.10, 0.15]))))
        total = Q(gross - disc)
        profit = Q(total * Decimal(str(margin * random.uniform(0.85, 1.15))))
        order_id = f"ORD-{oid:02d}-{i:05d}"
        rows.append([order_id, d, cid, cname, seg, pid, pname, pcat, qty, Q(price), disc, total, profit])
        mode, planned, _ = random.choices(MODES, [m[2] for m in MODES])[0]
        scheduled = d + dt.timedelta(days=planned)
        is_late = random.random() < late_rate and planned > 0
        actual = scheduled + dt.timedelta(days=random.randint(1, 3)) if is_late else scheduled
        ship.append([order_id, mode, "Late" if is_late else "On Time", scheduled, actual, (actual - d).days])

    # expected totals come from the valid rows only
    rev = sum(r[11] for r in rows); prof = sum(r[12] for r in rows); disc_tot = sum(r[10] for r in rows)
    anchor = max(r[1] for r in rows)
    def window(days): return sum(r[11] for r in rows if r[1] >= anchor - dt.timedelta(days=days - 1))
    by_prod, by_cat, by_mode = defaultdict(Decimal), defaultdict(Decimal), defaultdict(int)
    for r in rows: by_prod[r[6]] += r[11]; by_cat[r[7]] += r[11]
    for s in ship: by_mode[s[1]] += 1
    late_pct = round(100 * sum(1 for s in ship if s[2] == "Late") / len(ship), 2)
    expected[oid] = {
        "organization": name, "industry": industry, "valid_orders": len(rows),
        "revenue_total": str(rev), "avg_order_value": str(Q(rev / len(rows))),
        "total_profit": str(prof), "total_discount": str(disc_tot),
        "data_as_of": anchor.isoformat(), "revenue_last_7_days": str(window(7)), "revenue_last_30_days": str(window(30)),
        "top5_products_by_revenue": [[k, str(v)] for k, v in sorted(by_prod.items(), key=lambda kv: -kv[1])[:5]],
        "revenue_by_category": {k: str(v) for k, v in sorted(by_cat.items())},
        "shipments_by_mode": dict(by_mode), "late_delivery_percent": late_pct,
        "bad_rows_included": nbad}

    # bad rows (rejected by the cleaning rules); they are NOT in the expected totals
    bad = []
    for b in range(nbad):
        base = list(random.choice(rows))
        base[0] = f"ORD-{oid:02d}-9{b+1:04d}"
        kind = b % 3
        if kind == 0: base[8] = ""
        if kind == 1: base[8] = -2
        if kind == 2: base[1] = "not-a-date"
        bad.append([v.isoformat() if isinstance(v, dt.date) else str(v) if isinstance(v, Decimal) else v for v in base])
    ser = lambda v: v.isoformat() if isinstance(v, dt.date) else (str(v) if isinstance(v, Decimal) else v)
    out_rows = [[ser(v) for v in r] for r in rows]
    mixed = out_rows[:]
    for b_row in bad: mixed.insert(random.randint(0, len(mixed)), b_row)

    tag = f"org{oid:02d}"
    if oid in (3, 6):
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Orders"; ws.append(HEADER)
        for r in mixed:
            row = list(r)
            try: row[1] = dt.date.fromisoformat(row[1])
            except Exception: pass
            for j in (9, 10, 11, 12):
                try: row[j] = float(row[j])
                except Exception: pass
            try: row[8] = int(row[8])
            except Exception: pass
            ws.append(row)
        for rr in ws.iter_rows(min_row=2, min_col=2, max_col=2):
            for c in rr:
                if isinstance(c.value, dt.date): c.number_format = "DD/MM/YYYY"
        wb.save(f"{args.out}/{tag}_orders.xlsx"); ofile = f"{tag}_orders.xlsx"
    else:
        with open(f"{args.out}/{tag}_orders.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(HEADER); w.writerows(mixed)
        ofile = f"{tag}_orders.csv"
    with open(f"{args.out}/{tag}_shipping.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(SHIP_HEADER); w.writerows([[ser(v) for v in s] for s in ship])
    manifest.append([oid, name, industry, ofile, f"{tag}_shipping.csv", len(rows) + nbad, len(rows), nbad,
                     str(rev), anchor.isoformat(), late_pct])

with open(f"{args.out}/manifest.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["org_id","organization","industry","orders_file","shipping_file","rows_in_orders_file",
                "valid_orders","bad_rows","expected_revenue_inr","data_as_of","expected_late_percent"])
    w.writerows(manifest)
json.dump(expected, open(f"{args.out}/expected_totals.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("Done.", sum(m[5] for m in manifest), "order rows across", len(manifest), "organizations.")
