# Helios — Managed Data Warehouse & Analytics-as-a-Service for E-Commerce SMBs

> An enterprise-grade, multi-tenant analytics platform and managed lakehouse that automates data ingestion, Medallion ETL, and executive reporting for small and medium e-commerce businesses.

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. Tech Stack](#2-tech-stack)
- [3. Architecture](#3-architecture)
  - [The Medallion Lakehouse Flow](#the-medallion-lakehouse-flow)
  - [Three-Role Multi-Tenant Access Control](#three-role-multi-tenant-access-control)
- [4. Project Structure](#4-project-structure)
- [5. Prerequisites](#5-prerequisites)
- [6. Setup Instructions](#6-setup-instructions)
  - [Step 1: Clone the Repository](#step-1-clone-the-repository)
  - [Step 2: Environment Configuration](#step-2-environment-configuration)
  - [Step 3: Deploy Unity Catalog Schemas](#step-3-deploy-unity-catalog-schemas)
  - [Step 4: Seed Demo Tenants & Data](#step-4-seed-demo-tenants--data)
  - [Step 5: Bootstrap the System Administrator](#step-5-bootstrap-the-system-administrator)
- [7. Running the Project](#7-running-the-project)
  - [Option A: Running via Docker Compose](#option-a-running-via-docker-compose)
  - [Option B: Running Locally (Frontend & Backend Separately)](#option-b-running-locally-frontend--backend-separately)
- [8. Test Accounts](#8-test-accounts)
- [9. Key Features](#9-key-features)
  - [Organization Owner (Client Portal)](#organization-owner-client-portal)
  - [Team Member (Operations & Ingestion Engineering)](#team-member-operations--ingestion-engineering)
  - [Administrator (Global Governance & Platform Oversight)](#administrator-global-governance--platform-oversight)
- [10. Academic Note](#10-academic-note)

---

## 1. Overview

E-commerce Small and Medium Businesses (SMBs) struggle with fragmented data silos across payment processors, web stores, and shipping carriers, often lacking the in-house data engineering resources required to configure and maintain modern cloud data warehouses.

**Helios** bridges this gap by providing an end-to-end, multi-tenant Data Warehouse & Analytics-as-a-Service. The platform ingests disparate operational data via flat files, transactional database connections, or REST APIs, validates schemas via automated inference engines, processes the data through a curated Medallion Lakehouse architecture (Bronze &rarr; Silver &rarr; Gold) on Databricks Delta Lake, and surfaces executive dashboards, exportable reporting, and operational health telemetry.

> [!NOTE]
> **Glossary Note**: *An organization is called a tenant in the code.* Internal database tables, columns, repository methods, and API routes retain `tenant` (e.g., `tenant_id`, `/api/v1/tenants`, `/Volumes/helios/bronze/uploads/{tenant_id}/`), while user-facing interfaces, messages, exports, and documentation use **Organization** and **Organization Owner**. All monetary amounts across the platform are denominated in Indian Rupees (₹ / INR).

---

## 2. Tech Stack

| Layer | Technology | Purpose & Details |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript 5.6, Vite 6 | Single Page Application with dynamic chunking, lazy-loaded routes, and Tailwind CSS theming |
| **Data Visualization** | Recharts 2.15 | Responsive financial trends, late delivery risk, and performance charts |
| **Backend API** | FastAPI 0.111, Python 3.11+, Uvicorn | Asynchronous REST backend with Pydantic v2 schemas and modular dependency injection |
| **Lakehouse & Storage** | Databricks Unity Catalog, Delta Lake | Managed lakehouse storage with ACID transactions, schema enforcement, and time travel |
| **Warehouse Driver** | `databricks-sql-connector` 3.1, `pyarrow` | High-throughput, parameterized SQL execution and connection pooling |
| **RDBMS Connectors** | `psycopg2-binary`, `mysql-connector-python`, `pymssql` | Native client libraries for customer database ingestion (PostgreSQL, MySQL, SQL Server) |
| **Data Processing** | Pandas 2.0, RapidFuzz 3.0 | Schema inference, fuzzy column name matching, and currency/date normalization |
| **Reporting & Export** | ReportLab 4.0 | Server-side PDF executive summary and CSV tabular data generation |
| **Security & Auth** | PyJWT, Passlib (Bcrypt), Cryptography (Fernet) | JWT session auth, salted password hashing, and symmetric RDBMS credential encryption |
| **Orchestration** | Databricks Lakeflow Jobs, Databricks Asset Bundles (DAB) | Automated pipeline execution, scheduled Gold aggregation jobs, and workflow monitoring |
| **Testing** | Pytest, FastAPI TestClient, Vitest | Comprehensive backend unit/integration tests and frontend build validation |

---

## 3. Architecture

### The Medallion Lakehouse Flow

Helios organizes data into structured architectural layers within Databricks Unity Catalog:

```
[ Ingestion Sources ]
   │  ├── CSV / Excel File Uploads
   │  ├── External Database Sync (Postgres, MySQL, SQL Server)
   │  └── Programmatic REST API Push (X-API-Key)
   ▼
[ Bronze Layer ] (raw_orders, raw_shipping)
   │  Append-only raw landing table storing source payloads, batch metadata, and ingest timestamps.
   ▼
[ Silver Layer ] (orders_clean, shipping_clean)
   │  Cleansed and validated records: standardized ISO-8601 timestamps, currency parsing, 
   │  deduplication, and rejection logging to meta.data_quality_log.
   ▼
[ Gold Layer ] (Star Schema Mart)
   │  Dimensions: dim_date, dim_product, dim_customer, dim_shipping_mode, dim_delivery_status
   │  Facts:      fact_orders, fact_shipments, fact_orders_daily_summary
   ▼
[ Dashboards & Export ]
   Interactive analytics, dynamic date-filtering, and server-side PDF/CSV generation.
```

- **Bronze Layer (`bronze`)**: Raw immutable landing zone retaining original payloads, timestamps, batch IDs, and source provenance.
- **Silver Layer (`silver`)**: Cleansed and standardized tables with unified types, currency normalization, null handling, and quality checks. Records violating business constraints are rerouted to `meta.data_quality_log`.
- **Gold Layer (`gold`)**: Dimensional star schema powering performant analytical queries and daily summary aggregations (`fact_orders_daily_summary`).
- **Platform Layer (`platform`)**: Operational system catalog storing tenant configurations, user credentials, team assignments, API keys, schema definitions, and Unity Catalog Row-Level Security (RLS) filters.
- **Metadata Layer (`meta`)**: Centralized auditing recording ETL run durations, row counts, and data quality exceptions (`etl_audit_log`, `data_quality_log`).

### Three-Role Access Control

1. **Organization Owner (`smb_owner`)**: Customer organization accounts isolated by organization ID and catalog row-level security. Owners can only access their own data, ingestion pipelines, API keys, and business analytics.
2. **Team Member (`team_member`)**: Platform operators and data engineers assigned to specific organizations. Team members inspect staged uploads, verify inferred schemas, trigger/restart pipelines, and handle client support requests.
3. **Administrator (`admin`)**: Superusers with global system visibility. Admins manage organizations and user accounts, oversee cross-organization platform health, inspect system-wide data quality logs, and track aggregate infrastructure usage.

---

## 4. Project Structure

```
Helios/
├── backend/                       # FastAPI asynchronous REST API backend
│   ├── app/                       # Application logic (routers, core security, repositories, schemas)
│   │   ├── api/                   # Route handlers grouped by domain (auth, dashboard, uploads, etc.)
│   │   ├── core/                  # Configuration, JWT authentication, and dependency injection
│   │   ├── db/                    # Databricks SQL connection pool and session lifecycle
│   │   ├── repositories/          # Data access layer executing parameterized Delta queries
│   │   ├── schemas/               # Pydantic v2 validation models
│   │   └── services/              # Business logic (upload processing, notifications, oversight)
│   ├── scripts/                   # Administrative CLI utilities (bootstrap, load testing, benchmarks)
│   ├── tests/                     # Automated pytest test suites
│   ├── requirements.txt           # Python dependency specifications
│   └── .env.example               # Backend environment variable template
├── frontend/                      # React 18 / TypeScript SPA user interface
│   ├── src/                       # Application source code
│   │   ├── components/            # Reusable UI widgets, navigation bars, and chart containers
│   │   ├── hooks/                 # Custom React hooks (useTheme, useAuth)
│   │   ├── pages/                 # Role-based route views (client/, team/, admin/)
│   │   ├── routes/                # Central route registry with code-split lazy loading
│   │   └── services/              # Axios HTTP service wrappers
│   ├── package.json               # Node.js dependencies and script definitions
│   ├── vite.config.ts             # Vite build configuration with Rollup chunking
│   └── tailwind.config.js         # Design tokens, color palette, and dark mode configuration
├── database/                      # SQL DDL migrations and deployment runners
│   ├── 00_catalog_setup.sql       # Unity Catalog and schema initialization
│   ├── bronze/                    # Bronze raw landing table DDL definitions
│   ├── silver/                    # Silver clean table DDL definitions
│   ├── gold/                      # Gold star-schema tables and stored procedures
│   ├── platform/                  # Multi-tenant operational tables, users, and row filters
│   ├── meta/                      # Audit log and data quality reject tables
│   └── run_all.py                 # Automated sequential schema migration script
├── pipeline/                      # Medallion data engineering and ETL pipeline modules
│   ├── cleaning/                  # Silver cleaning logic (dates, currencies, deduplication, nulls)
│   ├── ingestion/                 # Bronze loaders and multi-format source readers
│   ├── schema_inference/          # Automated column fuzzy-matching and data type inference engine
│   └── demo/                      # Demo tenant seeding and DataCo supply chain sample data generator
├── data/                          # Seed datasets and demonstration fixtures
│   └── demo/                      # Pre-partitioned sample tenant CSV datasets
├── resources/                     # Databricks Asset Bundle definitions (Lakeflow workflows)
├── scripts/                       # Root-level utility scripts (bootstrap admin, load testing)
├── databricks.yml                 # Databricks CLI Asset Bundle configuration
└── README.md                      # Project documentation
```

---

## 5. Prerequisites

Before running Helios, ensure the following tools are installed:

- **Python**: Version `3.10` or higher (`3.11` recommended)
- **Node.js**: Version `18.x` or higher (LTS recommended) and `npm`
- **Docker & Docker Compose**: (Optional) For running containerized services
- **Databricks Workspace**:
  - Unity Catalog enabled
  - An active SQL Warehouse (Serverless or Pro)
  - Personal Access Token (PAT) with permissions to create catalogs, schemas, and tables

---

## 6. Setup Instructions

### Step 1: Clone the Repository

```bash
git clone https://github.com/heetdadhania/Helios.git
cd Helios
```

### Step 2: Environment Configuration

Copy the example environment configuration file to create your active backend `.env`:

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and populate your Databricks connection and security credentials:

```ini
# Application
ENVIRONMENT=development
PROJECT_NAME="Helios Multi-Tenant Data Platform"

# Security (Generate a 32-byte hex string: openssl rand -hex 32)
SECRET_KEY=your_super_secret_jwt_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Tenant Credential Encryption (Generate with cryptography.fernet.Fernet.generate_key())
CREDENTIAL_ENCRYPTION_KEY=your_fernet_32_byte_base64_encryption_key_here=

# Databricks SQL Warehouse Connection
DATABRICKS_SERVER_HOSTNAME=dbc-xxxxxxxx-xxxx.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/endpoints/xxxxxxxxxxxxxxxx
DATABRICKS_TOKEN=dapixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DATABRICKS_CATALOG=helios_catalog
DATABRICKS_SCHEMA=default

# Bootstrap Administrator
BOOTSTRAP_ADMIN_EMAIL=admin@helios.local
BOOTSTRAP_ADMIN_PASSWORD=your_secure_bootstrap_password!
```

### Step 3: Deploy Unity Catalog Schemas

Execute the master migration script to create all catalog schemas, platform tables, Medallion tables, stored procedures, and row-level security filters:

```bash
python database/run_all.py
```

### Step 4: Seed Demo Tenants & Data

Populate the database with pre-configured demo tenants (Apex Consumer Goods, Pacific Tech, Vanguard Home Office), assigned operators, and test records:

```bash
python pipeline/demo/seed_tenants.py --catalog helios_catalog
```

### Step 5: Bootstrap the System Administrator

Provision the primary platform administrator defined in your `.env` file:

```bash
python backend/scripts/bootstrap_admin.py
```

---

## 7. Running the Project

### Option A: Running via Docker Compose

Run the entire application stack (backend and frontend) with a single command:

```bash
docker-compose up --build
```

- **Frontend Application**: `http://localhost:5173`
- **Backend API Docs**: `http://localhost:8000/docs`

---

### Option B: Running Locally (Frontend & Backend Separately)

#### 1. Start the Backend API

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
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

The API will be available at `http://localhost:8000` with interactive Swagger docs at `http://localhost:8000/docs`.

#### 2. Start the Frontend Development Server

```bash
# In a separate terminal, navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

The frontend will be available at `http://localhost:5173`. Vite proxies `/api` requests directly to `http://localhost:8000`.

---

## 8. Test Accounts

The platform includes seeded test accounts covering each system persona.

> **Note on Passwords**: Passwords for seeded accounts are not hardcoded in this documentation. Refer to `BOOTSTRAP_ADMIN_PASSWORD` in your `backend/.env` file for the Administrator account, and `DEMO_PASSWORD_PLAIN` defined in `pipeline/demo/seed_tenants.py` (or your configured `TEST_ACCOUNT_PASSWORD` environment variable) for demo user accounts.

| Role | Name | Email | Organization | Access Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | Bootstrap Administrator | *(Configured in `.env`)* | Global | Full platform oversight, organization onboarding, system health |
| **Administrator** | Helios Admin | `admin@helios.io` | Global | Admin console, team assignments, global data quality logs |
| **Team Member** | Sarah Jenkins | `team@helios.io` | Assigned to Organizations 1 & 2 | Ingestion approval, pipeline triage, client support |
| **Organization Owner** | Aarav Sharma | `owner@apexconsumer.com` | Org 1: Kaveri Textiles & Crafts | Organization Portal: Home overview, INR analytics dashboards, CSV/PDF dataset export, notifications |
| **Organization Owner** | Rohan Kulkarni | `owner@pacifictech.com` | Org 2: Sahyadri Infotech Solutions | Client Portal, PostgreSQL database sync, INR analytics |
| **Organization Owner** | Ananya Iyer | `owner@vanguardhome.com` | Org 3: Nilgiri Home & Decor | Client Portal, REST API data push, API key management |

---

## 9. Key Features

### Organization Owner (Client Portal)
- **Multi-Channel Ingestion**: Upload batch files (CSV/Excel), configure external RDBMS database synchronization (PostgreSQL, MySQL, SQL Server), or stream records via REST API.
- **API Key Management**: Self-service creation, rolling revocation, and SHA-256 masking of API credentials.
- **Executive Analytics Dashboard**: Real-time business metrics including:
  - *Revenue & Profit Trends* (with 7-day, 30-day, and all-time date range filters)
  - *Top Selling Products & Profitability*
  - *Late Delivery Risk Analysis*
  - *Discount vs. Profit Margin Matrix*
  - *Shipping Mode Efficiency Comparison*
- **Report Exporting**: Generate formatted tabular CSV datasets and executive PDF summary briefs.
- **Integrated Support Desk**: Bi-directional communication channel with assigned data engineering operators.

### Team Member (Operations & Ingestion Engineering)
- **Schema Review & Confirmation**: Review incoming client file uploads with automated data type and column name suggestions; modify column mappings prior to Silver ingestion.
- **Pipeline Monitoring & Recovery**: Live status visualization across Medallion stages (Bronze, Silver, Gold), including retry and manual restart triggers for failed stages.
- **Data Quality Triage**: Real-time log of records rejected due to constraint failures or unparseable formats.
- **Client Support**: Direct response queue to resolve customer data ingestion issues.

### Administrator (Global Governance & Platform Oversight)
- **Organization Lifecycle Management**: Onboard new SMB organizations with automated namespace provisioning in Unity Catalog; activate or suspend organizations.
- **Operator Resource Allocation**: Assign and balance team member assignments across client organizations.
- **Cross-Organization Benchmarks**: Comparative platform metrics evaluating organization data volume, ingestion cadence, and health scores.
- **Infrastructure Auditing**: Centralized query history, latency distributions, and platform-wide ETL audit records.

---

## 10. Academic Note

Helios was developed as a Capstone Academic Project showcasing enterprise cloud lakehouse architecture, multi-tenant row-level security isolation, and automated Medallion data engineering on Databricks Unity Catalog and Delta Lake.
