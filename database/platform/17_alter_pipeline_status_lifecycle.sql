-- =====================================================================
-- Helios Platform Layer Migration: Add Pipeline Execution Lifecycle Columns
-- Safe, re-runnable DDL script adding heartbeat, failure diagnostics,
-- cancellation flags, and updated status lifecycle to platform.pipeline_status.
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

-- 1. Ensure table properties support column defaults
ALTER TABLE helios.platform.pipeline_status SET TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported');

-- 2. Drop any check constraint if present to allow new status lifecycle states
ALTER TABLE helios.platform.pipeline_status DROP CONSTRAINT IF EXISTS chk_pipeline_status_status;

-- 3. Add lifecycle and diagnostic columns only if not already present
BEGIN
  -- last_heartbeat_at (TIMESTAMP)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pipeline_status' AND column_name = 'last_heartbeat_at') = 0 THEN
    ALTER TABLE helios.platform.pipeline_status ADD COLUMNS (
      last_heartbeat_at TIMESTAMP COMMENT 'Timestamp of latest worker heartbeat during pipeline execution'
    );
  END IF;

  -- failed_stage (STRING)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pipeline_status' AND column_name = 'failed_stage') = 0 THEN
    ALTER TABLE helios.platform.pipeline_status ADD COLUMNS (
      failed_stage STRING COMMENT 'Stage where pipeline execution failed'
    );
  END IF;

  -- failure_message (STRING)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pipeline_status' AND column_name = 'failure_message') = 0 THEN
    ALTER TABLE helios.platform.pipeline_status ADD COLUMNS (
      failure_message STRING COMMENT 'Detailed error message or exception summary for pipeline failure'
    );
  END IF;

  -- failure_next_step (STRING)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pipeline_status' AND column_name = 'failure_next_step') = 0 THEN
    ALTER TABLE helios.platform.pipeline_status ADD COLUMNS (
      failure_next_step STRING COMMENT 'Recommended remediation or next step for pipeline failure'
    );
  END IF;

  -- cancel_requested (BOOLEAN default false)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pipeline_status' AND column_name = 'cancel_requested') = 0 THEN
    ALTER TABLE helios.platform.pipeline_status ADD COLUMNS (
      cancel_requested BOOLEAN COMMENT 'Flag indicating if operator requested cancellation'
    );
    ALTER TABLE helios.platform.pipeline_status ALTER COLUMN cancel_requested SET DEFAULT false;
  END IF;

  -- cancelled_by (BIGINT)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pipeline_status' AND column_name = 'cancelled_by') = 0 THEN
    ALTER TABLE helios.platform.pipeline_status ADD COLUMNS (
      cancelled_by BIGINT COMMENT 'Foreign key to platform.users who requested cancellation'
    );
  END IF;

  -- started_at (TIMESTAMP)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pipeline_status' AND column_name = 'started_at') = 0 THEN
    ALTER TABLE helios.platform.pipeline_status ADD COLUMNS (
      started_at TIMESTAMP COMMENT 'Execution start timestamp'
    );
  END IF;

  -- finished_at (TIMESTAMP)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pipeline_status' AND column_name = 'finished_at') = 0 THEN
    ALTER TABLE helios.platform.pipeline_status ADD COLUMNS (
      finished_at TIMESTAMP COMMENT 'Execution termination timestamp'
    );
  END IF;
END;

-- 4. Update status column documentation to reflect full lifecycle state model:
-- ingesting, pending_review, running, success, failed, rejected, cancelled, stalled
ALTER TABLE helios.platform.pipeline_status ALTER COLUMN status COMMENT 'Processing state: ingesting, pending_review, running, success, failed, rejected, cancelled, stalled';
