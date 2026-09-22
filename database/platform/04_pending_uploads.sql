-- =====================================================================
-- Helios Platform Layer: Pending Uploads Tracking
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

CREATE TABLE IF NOT EXISTS helios.platform.pending_uploads (
  upload_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing the tenant owner',
  source_type STRING NOT NULL COMMENT 'Ingestion method (upload, api_push, db_connection)',
  file_name STRING NOT NULL COMMENT 'Original file name uploaded by the tenant',
  file_path STRING NOT NULL COMMENT 'Cloud object storage URI (dbfs:/, s3://) holding the raw file',
  uploaded_by BIGINT COMMENT 'Foreign key to platform.users who triggered or authorized the upload',
  uploaded_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when upload was received',
  status STRING NOT NULL DEFAULT 'pending' COMMENT 'Upload lifecycle status: pending, approved, rejected, processing, completed',
  CONSTRAINT pk_pending_uploads PRIMARY KEY (upload_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Tracks files uploaded by tenants awaiting validation and approval';
