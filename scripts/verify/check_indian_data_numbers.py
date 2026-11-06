import json
import pandas as pd
from decimal import Decimal

with open('scripts/data/helios_indian_data/expected_totals.json') as f:
    expected = json.load(f)

for oid in [1, 4, 7]:
    exp = expected[str(oid)]
    df = pd.read_csv(f'scripts/data/helios_indian_data/org0{oid}_orders.csv')
    print(f"\n==================== Organization {oid} ====================")
    print(f"Total rows in CSV: {len(df)}")
    print(f"Expected valid orders: {exp['valid_orders']}, bad rows: {exp['bad_rows_included']}")

    # Cleaning rules from Silver cleaning:
    # 1. order_date valid
    # 2. quantity > 0 and not null
    # 3. unit_price > 0 and not null
    # 4. total > 0 and not null
    valid_df = df[
        (df['order_date'] != 'not-a-date') &
        (pd.to_datetime(df['order_date'], errors='coerce').notna()) &
        (pd.to_numeric(df['quantity'], errors='coerce') > 0) &
        (pd.to_numeric(df['total'], errors='coerce') >= 0)
    ].copy()

    print(f"Filtered valid rows count: {len(valid_df)}")
    valid_df['total_dec'] = valid_df['total'].apply(lambda x: Decimal(str(x)))
    tot_rev = valid_df['total_dec'].sum()
    print(f"Expected revenue: {exp['revenue_total']}, Computed: {tot_rev}, Diff: {abs(Decimal(exp['revenue_total']) - tot_rev)}")

    # Category Revenue
    cat_rev = valid_df.groupby('category')['total_dec'].sum().to_dict()
    print("Category Revenue:")
    for cat, rev in sorted(cat_rev.items()):
        exp_cat = exp['revenue_by_category'].get(cat, '0')
        print(f"  {cat}: {rev} (Expected: {exp_cat}, Diff: {abs(Decimal(exp_cat) - rev)})")

    # Segment Revenue
    seg_rev = valid_df.groupby('segment')['total_dec'].sum().to_dict()
    print("Segment Revenue:")
    for seg, rev in sorted(seg_rev.items()):
        pct = (rev / tot_rev * 100).quantize(Decimal("0.01"))
        print(f"  {seg}: {rev} ({pct}%)")

    # Monthly Revenue
    valid_df['month'] = valid_df['order_date'].str.slice(0, 7)
    month_rev = valid_df.groupby('month')['total_dec'].sum().to_dict()
    print("Monthly Revenue:")
    prev = None
    for m, rev in sorted(month_rev.items()):
        mom_pct = None
        if prev is not None:
            mom_pct = ((rev - prev) / prev * 100).quantize(Decimal("0.01"))
        print(f"  {m}: {rev} (MoM: {mom_pct}%)")
        prev = rev

