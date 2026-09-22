-- =====================================================================
-- Helios Gold Layer: Tenant-Scoped Product Dimension
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE TABLE IF NOT EXISTS helios.gold.dim_product (
  product_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing tenant ownership',
  product_name STRING NOT NULL COMMENT 'Standardized product title or SKU label',
  category STRING COMMENT 'Merchandise classification or taxonomy category',
  source_product_ref STRING COMMENT 'Source identifier or external SKU reference code',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when dimension entity was established',
  updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp of last entity modification',
  CONSTRAINT pk_dim_product PRIMARY KEY (product_id)
)
USING DELTA
PARTITIONED BY (tenant_id)
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Tenant-scoped product dimension containing catalog items and categorization';
