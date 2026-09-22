-- =====================================================================
-- Helios Silver Layer: Cleansed & Validated Orders Table
-- Conformed Transactional Layer with Validation Flags
-- =====================================================================

USE CATALOG helios;
USE SCHEMA silver;

CREATE TABLE IF NOT EXISTS helios.silver.orders_clean (
  clean_order_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing data owner',
  batch_id STRING NOT NULL COMMENT 'Ingestion batch UUID linking back to bronze stage',
  order_id STRING NOT NULL COMMENT 'Business order identifier from source system (e.g. Shopify, ERP)',
  customer_id STRING COMMENT 'Source system customer identifier or email reference',
  product_id STRING COMMENT 'Source system SKU or product reference',
  order_date TIMESTAMP COMMENT 'Parsed and standardized order timestamp (UTC)',
  quantity INT COMMENT 'Units ordered in line item',
  unit_price DECIMAL(18, 4) COMMENT 'Base unit price in tenant primary currency',
  total DECIMAL(18, 4) COMMENT 'Net line item amount after discount',
  discount DECIMAL(18, 4) COMMENT 'Discount applied to the line item amount',
  is_valid BOOLEAN NOT NULL DEFAULT true COMMENT 'Flag indicating if record passed all schema and range validations',
  rejection_reason STRING COMMENT 'Validation failure rationale if is_valid is false',
  processed_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when bronze record was transformed into silver',
  CONSTRAINT pk_orders_clean PRIMARY KEY (clean_order_id)
)
USING DELTA
PARTITIONED BY (tenant_id)
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Sanitized, validated, and typed order line items ready for gold dimension and fact loading';
