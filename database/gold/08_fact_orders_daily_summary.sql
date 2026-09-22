-- =====================================================================
-- Helios Gold Layer: Daily Orders Summary Aggregate Fact
-- High-Performance Dashboard Aggregate Table
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE TABLE IF NOT EXISTS helios.gold.fact_orders_daily_summary (
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing data owner',
  date_id BIGINT NOT NULL COMMENT 'Foreign key to gold.dim_date (calendar date in YYYYMMDD)',
  total_orders BIGINT NOT NULL DEFAULT 0 COMMENT 'Total distinct order transactions completed on this date',
  total_revenue DECIMAL(18, 4) NOT NULL DEFAULT 0.0000 COMMENT 'Aggregate gross revenue earned by tenant on this date',
  avg_order_value DECIMAL(18, 4) NOT NULL DEFAULT 0.0000 COMMENT 'Mean order basket size (total_revenue / total_orders)',
  total_quantity BIGINT NOT NULL DEFAULT 0 COMMENT 'Aggregate physical items ordered across all line items',
  updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when daily roll-up summary was last refreshed',
  CONSTRAINT pk_fact_orders_daily_summary PRIMARY KEY (tenant_id, date_id)
)
USING DELTA
PARTITIONED BY (tenant_id)
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Pre-aggregated daily sales and order performance roll-up powering client and admin KPI dashboards';
