-- =====================================================================
-- Helios Bronze Layer: Raw Orders Ingestion Table
-- Append-Only Raw Landing Zone for Tenant Orders
-- =====================================================================

USE CATALOG helios;
USE SCHEMA bronze;

CREATE TABLE IF NOT EXISTS helios.bronze.raw_orders (
  raw_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing data owner',
  batch_id STRING NOT NULL COMMENT 'Unique pipeline ingestion batch UUID',
  source_type STRING NOT NULL COMMENT 'Source channel: upload, db_connection, api_push',
  raw_row_json STRING NOT NULL COMMENT 'Immutable raw JSON representation of the incoming row payload',
  uploaded_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Landing timestamp into bronze storage',
  CONSTRAINT pk_raw_orders PRIMARY KEY (raw_id)
)
USING DELTA
PARTITIONED BY (tenant_id)
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Raw immutable landing zone for ingested order payloads (source_type: upload, db_connection, api_push)';
