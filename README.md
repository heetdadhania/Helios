# Helios: Multi-Tenant Cloud Data Platform & Analytics Engine

Helios is an enterprise-grade multi-tenant managed data warehouse and business intelligence platform designed specifically for Small and Midsize Businesses (SMBs) in the e-commerce and retail sectors. Powered by the **Databricks Lakehouse**, **Delta Lake**, and **Unity Catalog**, Helios provides an end-to-end Medallion Architecture (Bronze &rarr; Silver &rarr; Gold) that automates data ingestion, schema inference, data quality validation, and star-schema dimensional modeling.

The platform provides role-based workspaces tailored for **Organization Owners** (SMB decision makers), **Team Members** (Ingestion Engineers and Data Quality Analysts), and **Administrators** (Platform Governance and System Operators).

> **Glossary**:
> **An organization is called a tenant in the code.**
> All internal models, schemas, database tables, and API routes refer to `tenant` (e.g., `tenant_id`, `platform.tenants`), while the user interface, navigation menus, reports, and customer notifications consistently use **Organization** and **Organization Owner**.

---

## 1. System Architecture

Helios implements a Lakehouse Medallion Architecture running on Databricks Unity Catalog:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 INGESTION CHANNELS                                     │
│     Batch Files (CSV, Excel)  │  RDBMS Database Sync*  │  High-Throughput REST API*     │
│   *(Implemented; to be demonstrated in external viva — current demo covers CSV/Excel)   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  BRONZE LAYER (Raw Landing & Staging)                                                  │
│  - Raw file ingestion with metadata tracking (batch_id, tenant_id, file_name, ingested_at)│
│  - Automated column type inference and fuzzy header matching engine                    │
│  - Stored in Delta tables: bronze.raw_orders, bronze.raw_shipping                      │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  OPERATIONAL REVIEW & SCHEMA CONFIRMATION (Team & Admin Portals)                       │
│  - Pending uploads staged in platform.pending_uploads with duplicate check warnings     │
│  - Ingestion engineers review, override column mappings, and approve batches           │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  SILVER LAYER (Validated, Deduplicated & Cleansed)                                     │
│  - Date parsing, numeric normalization, and currency standardized to Indian Rupees (₹) │
│  - Primary key deduplication and business constraint enforcement                      │
│  - Quarantined malformed rows logged to meta.data_quality_log with explicit reasons     │
│  - Stored in Delta tables: silver.orders_clean, silver.shipping_clean                  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  GOLD LAYER (Star-Schema Analytics & Aggregation)                                      │
│  - Dimensions: gold.dim_date, gold.dim_product, gold.dim_customer,                     │
│                gold.dim_shipping_mode, gold.dim_delivery_status                        │
│  - Facts: gold.fact_orders, gold.fact_shipments, gold.fact_orders_daily_summary        │
│  - Strict multi-tenant isolation via Unity Catalog Row-Level Security (RLS) filters   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                                                    │
│  - Organization Owner Portal: Executive Analytics Dashboard (all values in ₹),         │
│    CSV/PDF export, notifications, support desk, profile management                     │
│  - Team Member Portal: Data ingestion, schema confirmation, pipeline health, DQ triage │
│  - Admin Console: Organization onboarding, team assignments, cross-org benchmarking    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

- **Frontend User Interface**:
  - **Framework**: React 18 with TypeScript
  - **Build Tooling**: Vite with Rollup code-splitting
  - **Styling**: Tailwind CSS (custom dark/light mode tokens)
  - **Data Visualization**: Recharts (revenue curves, profitability margin matrices, shipping performance)
  - **Icons**: Lucide React
  - **Form Validation**: React Hook Form with Zod schema validation
  - **HTTP Client**: Axios with automated bearer token injection and 401 interceptors

- **Backend REST API**:
  - **Framework**: FastAPI (Python 3.11 asynchronous web framework)
  - **Validation & Serialization**: Pydantic v2
  - **Lakehouse Connectivity**: Databricks SQL Connector for Python (`databricks-sql-connector`)
  - **Data Processing**: PyArrow, Pandas, OpenPyXL (Excel `.xlsx` parsing)
  - **Document Generation**: ReportLab (executive PDF briefs with embedded tables)
  - **Security & Cryptography**: PyJWT (HS256 tokens), Passlib with Bcrypt, Cryptography (Fernet symmetric credential encryption)

- **Cloud Data Warehouse & Storage**:
  - **Platform**: Databricks Unity Catalog on Delta Lake
  - **Catalog Namespace**: Three-level namespace (`helios_catalog.<schema>.<table>`)
  - **Security Isolation**: Delta Row-Level Security (RLS) row-filter functions

- **Infrastructure & Deployment**:
  - **Containers**: Docker and Docker Compose
  - **Web Server / Reverse Proxy**: Nginx (serving production SPA frontend bundle and routing `/api/v1`)

---

## 3. Directory Structure

```
Helios/
├── .env.example                       # Template for environment configuration
├── docker-compose.yml                 # Multi-container orchestration (backend + frontend)
├── databricks.yml                     # Databricks Asset Bundle definition
├── orders_30_valid.csv                # Verified sample dataset: 30 clean order records
├── orders_30_valid.xlsx               # Verified sample dataset: 30 clean order records in Excel
├── orders_30_valid_plus_3_bad.csv     # Verified sample dataset: 30 valid orders + 3 malformed rows
├── orders_10_renamed_headers.csv      # Verified sample dataset for schema mapping demonstration
├── shipping_30_for_valid_orders.csv   # Verified sample dataset: shipping events matching orders
│
├── backend/                           # FastAPI REST API Backend
│   ├── app/
│   │   ├── api/                       # API route handlers (/auth, /profile, /pipeline-health, etc.)
│   │   ├── core/                      # JWT auth, configuration settings, password security
│   │   ├── db/                        # Databricks SQL connection pool and session lifecycle
│   │   ├── models/                    # Data models and domain entities
│   │   ├── repositories/              # Parameterized SQL data access layer executing on Delta Lake
│   │   ├── schemas/                   # Pydantic v2 request/response schemas
│   │   ├── services/                  # Business logic (upload processing, notifications, exports)
│   │   └── main.py                    # FastAPI application factory and middleware configuration
│   ├── Dockerfile                     # Production backend Docker container image definition
│   └── requirements.txt               # Pinned Python package dependencies
│
├── frontend/                          # React 18 / TypeScript SPA Frontend
│   ├── src/
│   │   ├── components/                # Reusable UI widgets (TopBar, Sidebar, Modals, StatCards)
│   │   ├── hooks/                     # Custom React hooks (useAuth, useTheme, useNotifications)
│   │   ├── layouts/                   # Layout wrappers (AdminLayout, ClientLayout)
│   │   ├── pages/                     # Role-based route views
│   │   │   ├── admin/                 # Admin Home, Tenants, Team, PendingUploads, PipelineHealth, DQ
│   │   │   ├── auth/                  # ChangePassword guard
│   │   │   ├── client/                # ClientHome, Dashboard, ExportDataPage, Support, Notifications
│   │   │   ├── profile/               # Multi-role editable Profile page (name, phone, email, org)
│   │   │   ├── team/                  # TeamHome, IngestUpload, SupportInbox, TeamHistory
│   │   │   └── Login.tsx              # Multi-tenant authentication screen
│   │   ├── routes/                    # Role-based protected routes and redirect guards
│   │   ├── services/                  # Axios HTTP API service clients
│   │   ├── types/                     # TypeScript interface and type definitions
│   │   └── utils/                     # Formatting utilities (currency formatters in ₹, date helpers)
│   ├── Dockerfile                     # Multi-stage production Nginx frontend Docker container
│   ├── package.json                   # Node.js project manifest and build scripts
│   ├── vite.config.ts                 # Vite bundler configuration
│   └── tailwind.config.js             # Tailwind design tokens, typography, and dark mode theme
│
├── database/                          # Databricks Unity Catalog SQL DDL & Migration Scripts
│   ├── 00_catalog_setup.sql           # Catalog and schema initialization (platform, bronze, silver, gold, meta)
│   ├── bronze/                        # Bronze layer raw staging DDLs
│   │   ├── 01_raw_orders.sql
│   │   └── 02_raw_shipping.sql
│   ├── silver/                        # Silver layer cleansed and typed DDLs
│   │   ├── 01_orders_clean.sql
│   │   └── 02_shipping_clean.sql
│   ├── gold/                          # Gold star-schema dimension and fact DDLs
│   │   ├── 01_dim_date.sql ... 05_dim_delivery_status.sql
│   │   ├── 06_fact_orders.sql
│   │   ├── 07_fact_shipments.sql
│   │   ├── 08_fact_orders_daily_summary.sql
│   │   └── procedures/                # Stored procedures for ETL refresh
│   ├── platform/                      # Operational and multi-tenant catalog tables
│   │   ├── 01_tenants.sql ... 09_notification_log.sql
│   │   ├── 10_alter_inferred_schema_internal_notes.sql ... 18_backfill_new_columns.sql
│   │   └── row_filters.sql            # Unity Catalog Row-Level Security (RLS) filter definitions
│   ├── meta/                          # Governance, ETL telemetry, and data quality tables
│   │   ├── 01_etl_audit_log.sql       # Pipeline stage execution history
│   │   ├── 02_data_quality_log.sql    # Quarantined record log with rejection reasons
│   │   └── 03_audit_trail.sql         # Immutable operational and administrative audit events
│   ├── run_all.py                     # Automated sequential database migration runner
│   └── run_all.sql                    # Master SQL script for manual migration deployment
│
├── pipeline/                          # Medallion ETL & Data Processing Pipeline
│   ├── cleaning/                      # Silver cleansing, currency conversion to ₹, deduplication
│   ├── ingestion/                     # Bronze file parsing (CSV, Excel) and metadata attachment
│   ├── schema_inference/              # Automated column name matching and datatype inference
│   ├── runner.py                      # Core Medallion execution engine
│   └── submission.py                  # Batch ingestion submission coordinator
│
├── scripts/                           # Administrative, Data Seeding, and Verification Scripts
│   ├── seed_accounts.py               # Seeds 10 realistic organizations, owners, and 5 team members
│   ├── bootstrap_admin.py             # Provisions primary platform administrator
│   ├── load_test_login.py             # Concurrency and auth benchmarking utility
│   ├── data/                          # Demo dataset loaders and synthetic generators
│   └── verify/                        # Comprehensive test and security verification suites
│       ├── test_tenant_isolation.py   # RBAC, tenant boundary isolation, and profile security tests
│       ├── verify_step4_silver_rules.py# Silver cleansing rule verification
│       ├── verify_duplicate_and_merge.py# Duplicate detection and primary key collision tests
│       └── verify_dashboard_against_source.py # Data reconciliation between source and dashboards
│
├── data/                              # Demonstration datasets
│   └── demo/                          # Seed datasets for demo organizations
│
└── docs/                              # Project Documentation
    └── DEMO_SCRIPT.md                 # 10-minute step-by-step presentation script
```

---

## 4. Prerequisites

Before installing and running Helios, verify that your host environment meets the following specifications:

- **Python**: Version `3.10` or higher (`3.11` recommended)
- **Node.js**: Version `18.x` or higher (LTS recommended) and `npm`
- **Docker & Docker Compose**: (Optional, for containerized deployment) Docker Engine `24+`
- **Databricks Workspace**:
  - Unity Catalog enabled
  - Active SQL Warehouse (Serverless or Pro)
  - Personal Access Token (PAT) with administrative privileges to manage catalogs, schemas, and Delta tables

---

## 5. Environment Configuration

1. Create your local environment configuration file from the provided template:
   ```bash
   cp .env.example .env
   ```
   *(If running backend locally outside Docker, also copy to `backend/.env`: `cp .env.example backend/.env`)*

2. Open `.env` and fill in your Databricks connection details and security secrets.
   > **Security Note**: Never commit passwords or active tokens to version control. Passwords and tokens must be loaded strictly through environment variables.

   Key variables in `.env`:
   ```ini
   # Environment & Application
   ENVIRONMENT=development
   PROJECT_NAME="Helios Multi-Tenant Data Platform"
   API_V1_STR=/api/v1

   # Security (Generate a 32-byte hex string: openssl rand -hex 32)
   SECRET_KEY=your_super_secret_jwt_key_here_change_in_production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60

   # Symmetric Credential Encryption (Generate with cryptography.fernet.Fernet.generate_key())
   CREDENTIAL_ENCRYPTION_KEY=your_fernet_32_byte_base64_encryption_key_here=

   # Administrator & Test Account Credentials (Read from environment; never hardcode)
   ADMIN_PASSWORD=YourSecureAdminPassword123!
   TEST_ACCOUNT_PASSWORD=YourSecureTestAccountPassword123!

   # Databricks SQL Warehouse Connection
   DATABRICKS_SERVER_HOSTNAME=dbc-xxxxxxxx-xxxx.cloud.databricks.com
   DATABRICKS_HTTP_PATH=/sql/1.0/endpoints/xxxxxxxxxxxxxxxx
   DATABRICKS_TOKEN=dapixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   DATABRICKS_CATALOG=helios_catalog
   DATABRICKS_SCHEMA=default
   ```

3. Deploy database schemas, operational tables, and row-level security policies:
   ```bash
   python database/run_all.py
   ```

4. Seed the platform test accounts and organizations:
   ```bash
   python scripts/seed_accounts.py
   ```

5. Provision the platform bootstrap administrator:
   ```bash
   python scripts/bootstrap_admin.py
   ```

---

## 6. How to Run

### Option A: Running with Docker Compose (Recommended)

Run the full stack with a single command:
```bash
docker-compose up --build
```

- **Frontend User Interface**: `http://localhost:5173`
- **Backend API & Swagger Docs**: `http://localhost:8000/docs`
- **Backend Health Check**: `http://localhost:8000/api/v1/health`

### Option B: Running Locally (Without Docker)

#### 1. Start the Backend API Server
```bash
cd backend

# Create and activate Python virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The API is available at `http://localhost:8000` with Swagger documentation at `http://localhost:8000/docs`.

#### 2. Start the Frontend Development Server
```bash
# In a separate terminal, navigate to the frontend directory:
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```
The frontend is available at `http://localhost:5173`. Vite proxies `/api` calls directly to `http://localhost:8000`.

---

## 7. How to Load Test Data Through the Team Member Flow

> **CRITICAL ARCHITECTURAL RULE**:
> In Helios, **Organization Owners do NOT upload data directly.**
> E-commerce clients provide raw batch exports or database access, while ingestion, schema inspection, data cleansing, and Medallion pipeline execution are handled by **Team Members** (Data Engineers and Ingestion Analysts) and approved by **Administrators**.

Follow this flow to ingest datasets:

1. **Log in as Team Member**:
   - URL: `http://localhost:5173/login`
   - Email: `team-member-1@helios-test.dev`
   - Password: `$TEST_ACCOUNT_PASSWORD`

2. **Navigate to Upload Batch Screen**:
   - Click **Ingest & Upload** in the sidebar navigation or click **Upload File for Org** on the Team Home dashboard (`/team/upload`).

3. **Select Target Organization**:
   - Choose the organization to ingest data for from the assigned dropdown (e.g., *Tenant 1: Kaveri Textiles & Crafts*).

4. **Upload the Source File**:
   - Drag and drop or browse to select a clean test file:
     - `orders_30_valid.csv` (CSV format)
     - `orders_30_valid.xlsx` (Excel workbook format)
     - `orders_30_valid_plus_3_bad.csv` (Demonstrates data quality quarantining)

5. **Automatic Staging in Bronze**:
   - The file is uploaded and recorded in `platform.pending_uploads`.
   - Raw records land immediately in `bronze.raw_orders` with batch metadata.
   - The system executes automated column mapping, type inference, and duplicate primary key detection.
   - Batch status moves to `awaiting_confirmation`.

6. **Schema Review & Confirmation**:
   - Navigate to **Pending Uploads** (`/team/uploads` or `/admin/pending-uploads`).
   - Click **Review Schema** (`/admin/confirm-schema/{batch_id}`) to inspect inferred mappings, preview sample rows, and review any duplicate warnings.
   - Click **Approve & Trigger Pipeline**.

7. **Medallion Pipeline Execution**:
   - The backend runs Silver cleansing (`silver.orders_clean`), normalizing dates and formatting currency into ₹ while isolating malformed rows to `meta.data_quality_log`.
   - Gold dimensional transformations execute automatically (`gold.fact_orders`, `gold.fact_orders_daily_summary`).
   - Monitor real-time stage progression on the **Pipeline Health** dashboard (`/team/pipeline-health` or `/admin/pipeline-health`).

8. **Verify Ingested Analytics in the Organization Portal**:
   - Log in as the Organization Owner (`smb-owner-1@helios-test.dev`).
   - Open **Executive Dashboard** (`/client/dashboard`): all newly ingested revenue, profit, and order volumes appear immediately in Indian Rupees (₹).

---

## 8. User Roles & Capabilities

Helios enforces strict Role-Based Access Control (RBAC) across three distinct personas:

| Role | Primary Persona | Default Home URL | System Scope |
| :--- | :--- | :--- | :--- |
| **Administrator** (`admin`) | Platform Operations & Governance | `/admin/home` | Global platform oversight across all organizations |
| **Team Member** (`team_member`) | Ingestion Analyst & Data Engineer | `/team/home` | Scoped to assigned client organizations |
| **Organization Owner** (`smb_owner`) | SMB Executive / Store Owner | `/client/home` | Strictly isolated to own organization data via Unity Catalog RLS |

### Capabilities by Role

#### 1. Organization Owner (`smb_owner`)
- **Executive Analytics Dashboard**: Real-time business KPIs denominated in Indian Rupees (₹):
  - Total Revenue (₹), Net Profit (₹), Profit Margin (%), Total Orders, Average Order Value (₹)
  - Revenue & Profit Trends (7-day, 30-day, all-time filters)
  - Top Selling Products and product-level profitability
  - Late Delivery Risk distribution
  - Discount vs. Margin Matrix
  - Shipping Mode performance
- **Export Data**: One-click downloads of tabular CSV datasets and executive PDF summary briefs.
- **Support Desk**: Bi-directional messaging channel directly with assigned data engineering team members.
- **Notifications**: Real-time alerts for approved ingestion runs and pipeline status updates.
- **Editable Profile**: Update personal contact details (Name, Phone Number), request Email change with mandatory password confirmation, and update Organization metadata (Address, GSTIN, Website).

#### 2. Team Member (`team_member`)
- **Data Ingestion Engine**: Upload batch datasets (CSV, Excel) on behalf of assigned organizations.
- **Schema Review & Mapping**: Review automated type suggestions, override column definitions, and resolve mapping conflicts before Silver execution.
- **Pipeline Monitoring**: Live stage progression tracker (Bronze &rarr; Silver &rarr; Gold) with stage duration and error inspection.
- **Data Quality Triage**: Real-time inspection of rejected rows quarantined in `meta.data_quality_log`.
- **Support Inbox**: Manage and reply to incoming tickets from assigned organization owners.
- **Editable Profile**: Manage personal staff profile and credentials.

#### 3. Administrator (`admin`)
- **Platform Governance**: Complete oversight across all organizations, users, and pipelines.
- **Organization Lifecycle**: Onboard new SMB organizations, update corporate metadata, and activate or suspend accounts.
- **Operator Resource Allocation**: Assign and balance team member assignments across organizations.
- **Approval Queue**: Review and grant final approval for staged uploads across all organizations.
- **Pipeline Recovery**: Trigger stage-level retries or full batch restarts from the Pipeline Health dashboard.
- **Global Data Quality**: Enterprise-wide view of quarantined records and constraint failure trends.
- **Cross-Organization Benchmarking**: Comparative analysis of data volumes, ingestion cadence, and health scores.
- **Infrastructure Auditing**: Telemetry for query latency distributions, warehouse utilization, and audit logs.

---

## 9. Home Page of Each Role

Each role lands on an optimized Home cockpit immediately upon authentication:

1. **Organization Owner Home (`/client/home`)**:
   - Welcome banner displaying the organization business name and owner contact.
   - High-level business metric cards: Total Revenue (₹), Net Profit (₹), Total Orders, and Active Ingestion Status.
   - **Recent Ingestion Pipeline** status widget displaying the latest batch state and row counts.
   - **Assigned Team Member** contact card with a one-click button to open support messaging.
   - **Recent Activity & Notifications** feed highlighting completed runs or operational announcements.

2. **Team Member Home (`/team/home`)**:
   - **Assigned Organizations** roster highlighting active clients under the engineer's care.
   - Operational KPI widgets: *Pending Schema Reviews*, *Running Pipelines*, *DQ Exceptions Today*, and *Open Support Tickets*.
   - **Quick Action Bar**: "Upload File for Org", "Review Pending Uploads", and "Pipeline Health".
   - **Recent Pipeline Runs** live timeline table showing real-time batch progress across assigned clients.

3. **Admin Home (`/admin/home`)**:
   - Global Platform Telemetry banner showing overall lakehouse connectivity and system health.
   - Macro metric cards: Total Active Organizations, Total Ingested Platform Revenue (₹), Ingestion Health Score (%), and Open Review Queue.
   - **Global Pending Uploads** summary requiring immediate schema confirmation or review.
   - **Platform-Wide Data Quality** alert counter summarizing quarantined rows across all tenants.
   - Direct navigation shortcuts to Organization Management (`/admin/tenants`) and Infrastructure Usage (`/admin/usage`).

---

## 10. Currency & Naming Conventions

### Indian Rupee (₹ / INR) Convention
- All financial metrics across the entire application—including Executive Dashboards, summary cards, chart tooltips, tabular exports, PDF briefs, and SQL Gold aggregations—are strictly denominated and formatted in **Indian Rupees (₹)**.
- Example: `₹12,45,800.00` (Indian numerical grouping standard).

### Organization vs. Tenant Convention
- **User Interface, Documentation & Navigation**: The term **Organization** and **Organization Owner** is used exclusively.
- **Codebase, Database & API**: **An organization is called a tenant in the code.** Internal database tables (`platform.tenants`), columns (`tenant_id`), API paths (`/api/v1/tenants`), and SQL row filters use `tenant` for standard multi-tenant lakehouse design.

---

## 11. Platform Observability

Helios incorporates enterprise observability into its architecture:

### 1. Audit Tables
- **`meta.etl_audit_log`**: Records pipeline execution events by stage (`bronze_ingest`, `silver_clean`, `gold_transform`), including batch UUID, row volume processed, execution duration, completion timestamps, and full error stack traces upon failure.
- **`meta.audit_trail`**: Immutable security and governance log capturing administrative and operational events (e.g., `upload_approved`, `upload_rejected`, `profile_updated`, `organization_updated`, `pipeline_restarted`) with actor user ID, role, timestamp, justification reason, and JSON payload diffs.

### 2. Pipeline Status by Stage
- **`platform.pipeline_status`**: Tracks the real-time execution lifecycle of every ingestion batch through its Medallion progression:
  `bronze_ingest` &rarr; `schema_inference` &rarr; `awaiting_confirmation` &rarr; `silver_clean` &rarr; `gold_transform`.
- Status lifecycle states: `ingested`, `awaiting_confirmation`, `silver_running`, `gold_running`, `success`, `failed`, `restart_required`, `cancelled`.
- Records live worker heartbeats (`last_heartbeat_at`), failed stage indicators (`failed_stage`), and detailed failure diagnostics (`failure_message`).

### 3. Data Quality Log & Row-Level Quarantining
- **`meta.data_quality_log`**: When a record violates schema types or business constraints during Silver cleansing, Helios isolates the individual row into `meta.data_quality_log` without failing the overall pipeline.
- Recorded fields: `batch_id`, `tenant_id`, `table_name`, `row_identifier` (e.g. `order_id`), `rejection_reason` (e.g., `null_total`, `negative_quantity`, `invalid_date_format`), and `logged_at`.
- Clean records continue uninterrupted to Silver and Gold, guaranteeing pipeline resilience.

### 4. Notifications
- **`platform.notification_log`**: Targeted in-app notification events dispatched to specific users or broadcast across organization owners (e.g., upload approved, ingestion stage completed, pipeline failed, or profile updated). Displayed in the TopBar notification bell and dedicated notification feeds.

### 5. Failure Recovery: Retry and Restart
- **Stage-Level Retry (`POST /api/v1/pipeline-health/runs/{batch_id}/retry-failed-stage`)**:
  Re-executes only the failed stage (e.g., re-running Gold transformation after resolving a transient cluster timeout), preserving and reusing upstream cleaned Silver Delta data without reprocessing the raw source.
- **Full Batch Restart (`POST /api/v1/pipeline-health/runs/{batch_id}/full-restart`)**:
  Flags the batch as `restart_required` and alerts the assigned operator and organization owner to re-stage the file.
- **Run Cancellation (`POST /api/v1/pipeline-health/runs/{batch_id}/cancel`)**:
  Allows administrators to immediately terminate stuck or redundant pipeline jobs.

> **Ingestion Channel Status**:
> External Database Connection synchronization (PostgreSQL, MySQL, SQL Server) and High-Throughput REST API push are **implemented; to be demonstrated in the external viva**. This documentation and standard evaluation demo cover the end-to-end verified CSV and Excel ingestion pipelines.

---

## 12. Seeded Test Accounts

The platform includes pre-configured test accounts across all roles:

| Role | Name | Email | Organization Assignment |
| :--- | :--- | :--- | :--- |
| **Administrator** | Helios Admin | `admin@helios.io` | Global Platform Oversight |
| **Team Member** | Sunita Deshmukh | `team-member-1@helios-test.dev` | Tenant 1 (Kaveri Textiles) & Tenant 2 (Sahyadri Infotech) |
| **Team Member** | Kavita Reddy | `team-member-2@helios-test.dev` | Tenant 3 (Nilgiri Home) & Tenant 4 (AyurVeda Botanicals) |
| **Organization Owner** | Aarav Sharma | `smb-owner-1@helios-test.dev` | Tenant 1: Kaveri Textiles & Crafts |
| **Organization Owner** | Rohan Kulkarni | `smb-owner-2@helios-test.dev` | Tenant 2: Sahyadri Infotech Solutions |
| **Organization Owner** | Ananya Iyer | `smb-owner-3@helios-test.dev` | Tenant 3: Nilgiri Home & Decor |

*Account passwords match the `TEST_ACCOUNT_PASSWORD` and `ADMIN_PASSWORD` values defined in your environment configuration.*

---

## 13. Demonstration Script

For a comprehensive, step-by-step 10-minute presentation covering login, multi-role home cockpits, CSV/Excel ingestion, schema confirmation, pipeline health monitoring, INR dashboards, data quality rejection logs, and Databricks SQL reconciliation, refer to:

👉 **[docs/DEMO_SCRIPT.md](file:///c:/Project/Helios/docs/DEMO_SCRIPT.md)**
