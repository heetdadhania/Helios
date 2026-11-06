import os
import sys
import json
from decimal import Decimal
import pandas as pd

sys.path.insert(0, os.path.abspath('backend'))
from dotenv import load_dotenv
load_dotenv('backend/.env')
from app.db.base import get_databricks_connection
from app.core.config import settings

catalog = settings.DATABRICKS_CATALOG
conn = get_databricks_connection()
cur = conn.cursor()

results = {}

for oid in [1, 4, 7]:
    # 1. Pandas computation from source CSV
    df = pd.read_csv(f'scripts/data/helios_indian_data/org0{oid}_orders.csv')
    valid_df = df[
        (df['order_date'] != 'not-a-date') &
        (pd.to_datetime(df['order_date'], errors='coerce').notna()) &
        (pd.to_numeric(df['quantity'], errors='coerce') > 0) &
        (pd.to_numeric(df['total'], errors='coerce') >= 0)
    ].copy()
    valid_df['total_dec'] = valid_df['total'].apply(lambda x: Decimal(str(x)))
    valid_df['month'] = valid_df['order_date'].str.slice(0, 7)

    exp_cat = {k: str(v) for k, v in valid_df.groupby('category')['total_dec'].sum().items()}
    exp_seg = {k: str(v) for k, v in valid_df.groupby('segment')['total_dec'].sum().items()}
    exp_month = {k: str(v) for k, v in valid_df.groupby('month')['total_dec'].sum().items()}

    # 2. Database queries
    # Category
    q_cat = f"""
        SELECT coalesce(p.category, 'Uncategorized') as cat, round(sum(fo.total), 2) as rev
        FROM `{catalog}`.`gold`.`fact_orders` fo
        JOIN `{catalog}`.`gold`.`dim_product` p ON fo.product_id = p.product_id AND fo.tenant_id = p.tenant_id
        WHERE fo.tenant_id = :oid
        GROUP BY p.category
        ORDER BY rev DESC
    """
    cur.execute(q_cat, {'oid': oid})
    db_cat = {r[0]: str(r[1]) for r in cur.fetchall()}

    # Segment
    q_seg = f"""
        SELECT coalesce(c.segment, 'Other') as seg, round(sum(fo.total), 2) as rev
        FROM `{catalog}`.`gold`.`fact_orders` fo
        JOIN `{catalog}`.`gold`.`dim_customer` c ON fo.customer_id = c.customer_id AND fo.tenant_id = c.tenant_id
        WHERE fo.tenant_id = :oid
        GROUP BY c.segment
        ORDER BY rev DESC
    """
    cur.execute(q_seg, {'oid': oid})
    db_seg = {r[0]: str(r[1]) for r in cur.fetchall()}

    # Month
    q_month = f"""
        SELECT concat(cast(d.year as string), '-', lpad(cast(d.month as string), 2, '0')) as month_key, round(sum(fo.total), 2) as rev
        FROM `{catalog}`.`gold`.`fact_orders` fo
        JOIN `{catalog}`.`gold`.`dim_date` d ON fo.date_id = d.date_id
        WHERE fo.tenant_id = :oid
        GROUP BY d.year, d.month
        ORDER BY d.year ASC, d.month ASC
    """
    cur.execute(q_month, {'oid': oid})
    db_month = {r[0]: str(r[1]) for r in cur.fetchall()}

    results[oid] = {
        'category': {'expected': exp_cat, 'db': db_cat},
        'segment': {'expected': exp_seg, 'db': db_seg},
        'monthly': {'expected': exp_month, 'db': db_month},
    }

cur.close()
conn.close()

print(json.dumps(results, indent=2))

