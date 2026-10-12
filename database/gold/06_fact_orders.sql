-- =====================================================================
-- Helios Gold Layer: Orders Transaction Fact Table
-- Star Schema Central Transaction Grain
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE TABLE IF NOT EXISTS helios.gold.fact_orders (
  order_line_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing data owner',
  product_id BIGINT NOT NULL COMMENT 'Foreign key to gold.dim_product surrogate key',
  customer_id BIGINT NOT NULL COMMENT 'Foreign key to gold.dim_customer surrogate key',
  date_id BIGINT NOT NULL COMMENT 'Foreign key to gold.dim_date (order placement date in YYYYMMDD)',
  quantity INT NOT NULL COMMENT 'Units purchased in this line item',
  unit_price DECIMAL(18, 4) NOT NULL COMMENT 'Unit sale price at time of purchase',
  discount DECIMAL(18, 4) NOT NULL DEFAULT 0.0000 COMMENT 'Discount amount applied to line total',
  total DECIMAL(18, 4) NOT NULL COMMENT 'Net revenue amount for this line item',
  profit DECIMAL(18, 4) COMMENT 'Calculated gross profit contribution after estimated product cost',
  source_order_id STRING COMMENT 'Natural source system order identifier',
  source_order_line_key STRING COMMENT 'Natural source order line identifier',
  batch_id STRING NOT NULL COMMENT 'Ingestion batch UUID linking through silver and bronze',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Record insertion timestamp into gold layer',
  CONSTRAINT pk_fact_orders PRIMARY KEY (order_line_id)
)
USING DELTA
PARTITIONED BY (tenant_id)
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Core transactional order line fact table powering revenue, volume, and customer analytics';
