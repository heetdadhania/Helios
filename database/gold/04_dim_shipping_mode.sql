-- =====================================================================
-- Helios Gold Layer: Conformed Shipping Mode Dimension
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE TABLE IF NOT EXISTS helios.gold.dim_shipping_mode (
  shipping_mode_id BIGINT GENERATED ALWAYS AS IDENTITY,
  mode_name STRING NOT NULL COMMENT 'Standardized shipping channel: Standard Ground, Express Air, Same Day, Freight',
  description STRING COMMENT 'Descriptive SLA or carrier details for the fulfillment method',
  CONSTRAINT pk_dim_shipping_mode PRIMARY KEY (shipping_mode_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Conformed lookup dimension for standardized logistics and fulfillment modes';
