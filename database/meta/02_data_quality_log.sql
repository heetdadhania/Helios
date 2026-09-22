-- =====================================================================
-- Helios Meta Layer: Data Quality Validation Log
-- =====================================================================

USE CATALOG helios;
USE SCHEMA meta;

CREATE TABLE IF NOT EXISTS helios.meta.data_quality_log (
  log_id BIGINT GENERATED ALWAYS AS IDENTITY,
  batch_id STRING NOT NULL COMMENT 'Pipeline execution batch identifier UUID',
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing the dataset owner',
  table_name STRING NOT NULL COMMENT 'Target Delta table where data quality check failed (e.g. silver.orders_clean)',
  row_identifier STRING COMMENT 'Business primary key or unique identifier of the malformed record (e.g. order_id)',
  rejection_reason STRING NOT NULL COMMENT 'Detailed explanation of why record was rejected or flagged (e.g. null_total, invalid_date)',
  logged_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when validation failure was detected and logged',
  CONSTRAINT pk_data_quality_log PRIMARY KEY (log_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Records row-level data quality rejections, validation rule failures, and schema anomalies';
