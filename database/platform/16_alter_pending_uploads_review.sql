-- =====================================================================
-- Helios Platform Layer Migration: Add Review & Decision Tracking
-- Safe, re-runnable DDL script adding review decision and hash columns
-- to platform.pending_uploads.
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

BEGIN
  -- file_hash (STRING)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pending_uploads' AND column_name = 'file_hash') = 0 THEN
    ALTER TABLE helios.platform.pending_uploads ADD COLUMNS (
      file_hash STRING COMMENT 'Cryptographic hash (e.g. SHA-256) of uploaded raw file'
    );
  END IF;

  -- decision (STRING: 'approved'/'rejected')
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pending_uploads' AND column_name = 'decision') = 0 THEN
    ALTER TABLE helios.platform.pending_uploads ADD COLUMNS (
      decision STRING COMMENT 'Review decision: approved or rejected'
    );
  END IF;

  -- decision_reason (STRING)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pending_uploads' AND column_name = 'decision_reason') = 0 THEN
    ALTER TABLE helios.platform.pending_uploads ADD COLUMNS (
      decision_reason STRING COMMENT 'Explanation or reviewer justification for review decision'
    );
  END IF;

  -- decided_by (BIGINT)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pending_uploads' AND column_name = 'decided_by') = 0 THEN
    ALTER TABLE helios.platform.pending_uploads ADD COLUMNS (
      decided_by BIGINT COMMENT 'Foreign key to platform.users for reviewer who decided upload'
    );
  END IF;

  -- decided_at (TIMESTAMP)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'pending_uploads' AND column_name = 'decided_at') = 0 THEN
    ALTER TABLE helios.platform.pending_uploads ADD COLUMNS (
      decided_at TIMESTAMP COMMENT 'Timestamp when review decision was recorded'
    );
  END IF;
END;
