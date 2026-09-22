-- =====================================================================
-- Helios Platform Layer: Pipeline Execution Status
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

CREATE TABLE IF NOT EXISTS helios.platform.pipeline_status (
  batch_id STRING NOT NULL COMMENT 'Unique pipeline execution batch UUID',
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing the tenant owner',
  upload_id BIGINT COMMENT 'Optional foreign key to platform.pending_uploads if triggered by file upload',
  stage STRING NOT NULL COMMENT 'Current pipeline step: bronze_ingest, schema_inference, silver_clean, gold_transform',
  status STRING NOT NULL COMMENT 'Processing state: ingested, schema_inference_running, awaiting_confirmation, silver_running, gold_running, success, failed',
  error_message STRING COMMENT 'Detailed error stack trace or message if execution failed',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Batch initiation timestamp',
  updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp of last state modification',
  CONSTRAINT pk_pipeline_status PRIMARY KEY (batch_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Tracks state and stage progression for Medallion ETL batches across tenants';
