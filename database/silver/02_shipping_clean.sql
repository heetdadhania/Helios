-- =====================================================================
-- Helios Silver Layer: Cleansed & Validated Shipping Table
-- Conformed Logistics Layer with Timeliness Calculations
-- =====================================================================

USE CATALOG helios;
USE SCHEMA silver;

CREATE TABLE IF NOT EXISTS helios.silver.shipping_clean (
  clean_shipping_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing data owner',
  batch_id STRING NOT NULL COMMENT 'Ingestion batch UUID linking back to bronze stage',
  order_id STRING NOT NULL COMMENT 'Source order reference matching silver.orders_clean.order_id',
  shipping_mode STRING COMMENT 'Delivery method (Standard, Express, Next Day, Freight)',
  delivery_status STRING COMMENT 'Current shipment status (Delivered, In Transit, Returned, Cancelled)',
  scheduled_date TIMESTAMP COMMENT 'Promised or anticipated delivery timestamp',
  actual_date TIMESTAMP COMMENT 'Actual confirmed delivery timestamp',
  shipping_days INT COMMENT 'Calculated elapsed duration in calendar days from dispatch to delivery',
  is_valid BOOLEAN NOT NULL DEFAULT true COMMENT 'Flag indicating if shipping record passed all domain validations',
  rejection_reason STRING COMMENT 'Validation failure rationale if is_valid is false',
  processed_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when bronze record was transformed into silver',
  CONSTRAINT pk_shipping_clean PRIMARY KEY (clean_shipping_id)
)
USING DELTA
PARTITIONED BY (tenant_id)
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Sanitized and validated shipping/fulfillment records with standardized dates and delivery status';
