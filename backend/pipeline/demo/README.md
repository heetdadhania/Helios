# Helios Multi-Organization Demo Data & Onboarding Guide

This module provides data preparation and environment seeding scripts to showcase the **Helios Multi-Organization Data Platform** using the **DataCo Smart Supply Chain Dataset**.

> [!NOTE]
> **Glossary Note**: *An organization is called a tenant in the code.* Internal database tables, columns, repository methods, and API routes retain `tenant` (e.g., `tenant_id`, `/api/v1/tenants`), while user-facing interfaces, messages, exports, and documentation use **Organization** and **Organization Owner**.

---

## 1. Simulated Demo Organizations

The DataCo supply chain dataset is partitioned across **Market** and **Customer Segment** dimensions into distinct simulated e-commerce organizations:

| Organization ID | Organization Name | Market | Segment | Industry Vertical | Primary Channel | Data File |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Org 1** | **Kaveri Textiles & Crafts** | South Asia | Consumer | Apparel & Textiles | File Upload (CSV) | `data/demo/tenant_1_apex_consumer.csv` |
| **Org 2** | **Sahyadri Infotech Solutions** | South Asia | Corporate | Electronics & Hardware | Database Connection | `data/demo/tenant_2_pacific_tech.csv` |
| **Org 3** | **Nilgiri Home & Decor** | South Asia | Home Office | Home Goods & Living | REST API Push | `data/demo/tenant_3_vanguard_home.csv` |

---

## 2. Demo User Accounts & Credentials

| Role | Name | Email | Organization Affiliation | Accessible Portals & Features |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | Helios Admin | `admin@helios.io` | *Global (All Organizations)* | Admin Console: Organization management, User management, Pending approvals, Pipeline Health, Data Quality audit |
| **Team Member** | Sarah Jenkins | `team@helios.io` | *Assigned to Organizations 1 & 2* | Admin Console: Schema confirmations, Pipeline repair/restart, Data quality triage for assigned organizations |
| **Organization Owner** | Aarav Sharma | `owner@apexconsumer.com` | **Org 1** (Kaveri Textiles) | Organization Portal: Home overview, INR analytics dashboards, CSV/PDF dataset export, notifications |
| **Organization Owner** | Rohan Kulkarni | `owner@pacifictech.com` | **Org 2** (Sahyadri Infotech) | Client Portal: Database connections & sync, INR analytics dashboards, CSV/PDF dataset export |
| **Organization Owner** | Ananya Iyer | `owner@vanguardhome.com` | **Org 3** (Nilgiri Home) | Client Portal: API key regeneration & docs, INR analytics dashboards, CSV/PDF dataset export |

---

## 3. The Three Ingestion Methods

Helios supports three distinct ingestion pathways. The demo environment is pre-configured to test all three:

### Method 1: File Upload (CSV / Excel)
- **Actor**: Sarah Jenkins (`team@helios.io`, Team Member assigned to Org 1)
- **Demo File**: `data/demo/tenant_1_apex_consumer.csv`
- **Workflow**:
  1. Log into the Operations Portal at `/login` using `team@helios.io`.
  2. Navigate to **Upload Data** (`/admin/upload`) &rarr; select assigned organization (Org 1).
  3. Drag and drop `data/demo/tenant_1_apex_consumer.csv` and submit.
  4. Ingestion creates a batch in `pending_review` status.
  5. Go to **Pending Uploads** &rarr; review inferred schema &rarr; **Confirm Schema**.
  6. Databricks Lakeflow job executes Silver cleaning and Gold procedures (`sp_run_gold_pipeline`).
  7. Client notification fires: *"Your dashboard is ready to view"*.

### Method 2: Managed Database Connection (RDBMS Sync)
- **Actor**: Elena Rostova (`owner@pacifictech.com`, Tenant 2)
- **Pre-seeded Connection**:
  - **Engine**: PostgreSQL (`db_type = 'postgresql'`)
  - **Host / Port**: `demo-pg.helios.internal:5432`
  - **Database**: `pacific_ecom_prod`
  - **Table / Query**: `SELECT * FROM daily_transactions WHERE status = 'COMPLETED'`
  - **Secret Reference**: `helios_tenant_2:helios-tenant-2-conn-demo1` (managed in Databricks Secrets)
- **Workflow**:
  1. Log into the Client Portal as `owner@pacifictech.com`.
  2. Navigate to **Data Sources** &rarr; click **Connect Database**.
  3. Review the existing pre-configured connection or test a new MySQL/PostgreSQL endpoint.
  4. Click **Sync Now** to trigger an immediate extraction.
  5. Extracted rows are streamed via TLS/SSL into Unity Catalog Bronze landing zone `helios.bronze.raw_orders`.

### Method 3: Programmatic API Push (REST Ingestion)
- **Actor**: David Kim (`owner@vanguardhome.com`, Tenant 3)
- **Pre-seeded API Key**:
  - **Raw API Key**: `helios_live_vanguard_demo_api_key_2026`
  - **Masked Display**: `helios_live_••••2026`
  - **Hash (SHA-256)**: `3837fdf31054d3137cabe83084aa3a12ac62864398667bfd444c451a3982272c`
- **Workflow**:
  1. Send an HTTP `POST` request to the Helios Ingestion endpoint with the API key header:

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/push" \
  -H "Content-Type: application/json" \
  -H "X-Helios-Api-Key: helios_live_vanguard_demo_api_key_2026" \
  -d '{
    "records": [
      {
        "order_id": "130001",
        "customer_id": "3501",
        "product_name": "Ergonomic Mesh Office Executive Chair",
        "sales": 249.99,
        "order_item_quantity": 2,
        "order_date": "2026-06-01 10:15:00",
        "shipping_mode": "Standard Class",
        "market": "USCA",
        "delivery_status": "Advance shipping"
      }
    ]
  }'
```

2. The endpoint authenticates against `platform.api_keys`, applies rate limiting (60 req/min), stamps `tenant_id = 3`, and appends the payload into `helios.bronze.raw_orders`.

---

## 4. Scripts Execution Reference

### A. Data Preparation (`prepare_demo_tenants.py`)
Generates 3 partitioned CSV files adhering strictly to the 53-column DataCo supply chain schema:

```bash
# Option 1: Generate realistic synthetic DataCo demo data (no download needed)
python pipeline/demo/prepare_demo_tenants.py --output-dir data/demo --max-rows 500

# Option 2: Split an existing DataCoSupplyChainDataset.csv
python pipeline/demo/prepare_demo_tenants.py --input-csv path/to/DataCoSupplyChainDataset.csv --output-dir data/demo
```

### B. Platform Seeding (`seed_tenants.py`)
Provisions tenants, users with bcrypt password hashes, team assignments, demo DB connection, and API key:

```bash
# Dry run: view generated SQL statements and export to file
python pipeline/demo/seed_tenants.py --dry-run --sql-output pipeline/demo/seed_data.sql

# Live run: execute statements directly against Databricks Unity Catalog
python pipeline/demo/seed_tenants.py --catalog helios_catalog
```
