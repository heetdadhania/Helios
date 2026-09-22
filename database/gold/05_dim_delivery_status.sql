-- =====================================================================
-- Helios Gold Layer: Conformed Delivery Status Dimension
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE TABLE IF NOT EXISTS helios.gold.dim_delivery_status (
  delivery_status_id BIGINT GENERATED ALWAYS AS IDENTITY,
  status_name STRING NOT NULL COMMENT 'Standardized fulfillment status: Delivered, In Transit, Out for Delivery, Failed, Returned',
  is_terminal BOOLEAN NOT NULL DEFAULT false COMMENT 'True if status represents final lifecycle state (Delivered or Returned)',
  CONSTRAINT pk_dim_delivery_status PRIMARY KEY (delivery_status_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Conformed lookup dimension for standardized fulfillment and delivery progress states';
