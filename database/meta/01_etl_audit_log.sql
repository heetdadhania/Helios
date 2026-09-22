-- =====================================================================
-- Helios Meta Layer: ETL Pipeline Execution Audit Log
-- =====================================================================

USE CATALOG helios;
USE SCHEMA meta;

CREATE TABLE IF NOT EXISTS helios.meta.etl_audit_log (
  log_id BIGINT GENERATED ALWAYS AS IDENTITY,
  batch_id STRING NOT NULL COMMENT 'Pipeline execution batch identifier UUID',
  stage STRING NOT NULL COMMENT 'ETL pipeline stage: bronze_ingest, silver_clean, gold_transform',
  row_count BIGINT COMMENT 'Number of rows processed during this stage execution',
  status STRING NOT NULL COMMENT 'Stage status: started, in_progress, completed, failed',
  started_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Execution start timestamp',
  completed_at TIMESTAMP COMMENT 'Execution termination or success timestamp',
  error_message STRING COMMENT 'Detailed error message and failure stack if execution failed',
  CONSTRAINT pk_etl_audit_log PRIMARY KEY (log_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Audit history recording start, completion, row volumes, and errors across pipeline stages';
