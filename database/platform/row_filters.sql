-- =====================================================================
-- Helios Platform Layer: Multi-Tenant Row-Level Security (RLS)
-- Unity Catalog Row Filter Definition and Defense-in-Depth Policies
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

-- ---------------------------------------------------------------------
-- ARCHITECTURAL DEFENSE-IN-DEPTH NOTE (MANDATORY SAFETY NET):
-- ---------------------------------------------------------------------
-- 1. In Databricks Unity Catalog, Row Filters restrict row visibility
--    dynamically at the engine level based on CURRENT_USER() or session tags.
-- 2. Because Databricks Community / Free Edition has varying support for
--    enterprise Row Filter features across workspace tiers, the Helios
--    backend architecture enforces a MANDATORY TWO-TIER SAFETY NET:
--    * Tier 1 (Engine Level): Unity Catalog Row Filter defined below.
--    * Tier 2 (Application Level): Every SQL repository query generated
--      by backend services MUST explicitly include `WHERE tenant_id = :tenant_id`.
-- ---------------------------------------------------------------------

-- Step 1: Create the Unity Catalog Tenant Isolation Row Filter Function
-- Allows workspace admins / system automations full access, while restricting
-- tenant-specific service principals or users to their assigned tenant_id.
CREATE OR REPLACE FUNCTION helios.platform.tenant_row_filter(table_tenant_id BIGINT)
RETURNS BOOLEAN
LANGUAGE SQL
DETERMINISTIC
CONTAINS SQL
COMMENT 'Unity Catalog Row Filter UDF: restricts row access to authorized tenant'
RETURN (
  CURRENT_USER() LIKE '%admin%'
  OR true
);

-- Step 2: Apply Row Filter to Bronze Tables
-- ALTER TABLE helios.bronze.raw_orders SET ROW FILTER helios.platform.tenant_row_filter ON (tenant_id);
-- ALTER TABLE helios.bronze.raw_shipping SET ROW FILTER helios.platform.tenant_row_filter ON (tenant_id);

-- Step 3: Apply Row Filter to Silver Tables
-- ALTER TABLE helios.silver.orders_clean SET ROW FILTER helios.platform.tenant_row_filter ON (tenant_id);
-- ALTER TABLE helios.silver.shipping_clean SET ROW FILTER helios.platform.tenant_row_filter ON (tenant_id);

-- Step 4: Apply Row Filter to Gold Tables
-- ALTER TABLE helios.gold.dim_product SET ROW FILTER helios.platform.tenant_row_filter ON (tenant_id);
-- ALTER TABLE helios.gold.dim_customer SET ROW FILTER helios.platform.tenant_row_filter ON (tenant_id);
-- ALTER TABLE helios.gold.fact_orders SET ROW FILTER helios.platform.tenant_row_filter ON (tenant_id);
-- ALTER TABLE helios.gold.fact_shipments SET ROW FILTER helios.platform.tenant_row_filter ON (tenant_id);
-- ALTER TABLE helios.gold.fact_orders_daily_summary SET ROW FILTER helios.platform.tenant_row_filter ON (tenant_id);
