-- =====================================================================
-- Helios Gold Layer: Shipments Fact Table
-- Star Schema Fulfillment & Delivery Performance Fact
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE TABLE IF NOT EXISTS helios.gold.fact_shipments (
  shipment_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing data owner',
  order_line_id BIGINT COMMENT 'Optional foreign key to gold.fact_orders.order_line_id',
  shipping_mode_id BIGINT NOT NULL COMMENT 'Foreign key to gold.dim_shipping_mode surrogate key',
  delivery_status_id BIGINT NOT NULL COMMENT 'Foreign key to gold.dim_delivery_status surrogate key',
  date_id BIGINT NOT NULL COMMENT 'Foreign key to gold.dim_date representing ship or delivery date',
  shipping_days INT COMMENT 'Actual transit duration in calendar days',
  scheduled_days INT COMMENT 'Target or promised delivery duration in days',
  late_flag BOOLEAN NOT NULL DEFAULT false COMMENT 'True if actual delivery exceeded scheduled delivery deadline',
  source_order_id STRING COMMENT 'Natural source order reference',
  source_order_line_key STRING COMMENT 'Natural source order line identifier',
  batch_id STRING NOT NULL COMMENT 'Ingestion batch UUID linking through silver and bronze',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Record insertion timestamp into gold layer',
  CONSTRAINT pk_fact_shipments PRIMARY KEY (shipment_id)
)
USING DELTA
PARTITIONED BY (tenant_id)
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Shipments and logistics fact table measuring carrier performance and delivery SLA compliance';
