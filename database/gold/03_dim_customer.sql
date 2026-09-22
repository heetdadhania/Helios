-- =====================================================================
-- Helios Gold Layer: Tenant-Scoped Customer Dimension
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE TABLE IF NOT EXISTS helios.gold.dim_customer (
  customer_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing tenant ownership',
  customer_name STRING NOT NULL COMMENT 'Consolidated customer name or corporate entity title',
  segment STRING COMMENT 'Market cohort or marketing tier: VIP, Repeat, New, Wholesale, Churned',
  email STRING COMMENT 'Masked or canonical customer contact identifier',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Customer dimension establishment timestamp',
  updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp of last profile update',
  CONSTRAINT pk_dim_customer PRIMARY KEY (customer_id)
)
USING DELTA
PARTITIONED BY (tenant_id)
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Tenant-scoped customer dimension providing demographic and behavioral segmentation';
