-- =====================================================================
-- Helios Platform Layer Migration: Add Staff Details & Password Reset Flag
-- Safe, re-runnable DDL script adding staff profile metadata and security
-- columns to platform.users.
-- Uses information_schema checks inside a Databricks compound procedural
-- block to ensure safe, idempotent execution even if partially applied.
-- =====================================================================

USE CATALOG helios_catalog;
USE SCHEMA platform;

-- ---------------------------------------------------------------------
-- 1. Pre-Migration Inspection: Review existing schema via information_schema
-- ---------------------------------------------------------------------
SELECT
  column_name,
  data_type,
  is_nullable,
  column_default,
  comment
FROM helios_catalog.information_schema.columns
WHERE table_schema = 'platform'
  AND table_name = 'users'
ORDER BY ordinal_position;

-- ---------------------------------------------------------------------
-- 2. Schema Alterations: Add staff columns only if not already present
-- ---------------------------------------------------------------------
BEGIN
  -- 1. phone_number (STRING, nullable)
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'users' AND column_name = 'phone_number') = 0 THEN
    ALTER TABLE helios_catalog.platform.users ADD COLUMNS (
      phone_number STRING COMMENT 'Staff or user contact phone number (nullable)'
    );
  END IF;

  -- 2. staff_id (STRING, nullable)
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'users' AND column_name = 'staff_id') = 0 THEN
    ALTER TABLE helios_catalog.platform.users ADD COLUMNS (
      staff_id STRING COMMENT 'Staff employee identifier or badge ID (nullable)'
    );
  END IF;

  -- 3. designation (STRING, nullable)
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'users' AND column_name = 'designation') = 0 THEN
    ALTER TABLE helios_catalog.platform.users ADD COLUMNS (
      designation STRING COMMENT 'Staff job title or organizational role designation (nullable)'
    );
  END IF;

  -- 4. must_change_password (BOOLEAN, default false)
  -- Note: Delta tables require adding column first, then setting default via ALTER COLUMN
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'users' AND column_name = 'must_change_password') = 0 THEN
    ALTER TABLE helios_catalog.platform.users ADD COLUMNS (
      must_change_password BOOLEAN COMMENT 'Flag indicating if user must reset password on next login'
    );
    ALTER TABLE helios_catalog.platform.users ALTER COLUMN must_change_password SET DEFAULT false;
  END IF;
END;

-- ---------------------------------------------------------------------
-- 3. Post-Migration Verification: Verify all 4 columns in information_schema
-- ---------------------------------------------------------------------
SELECT
  column_name,
  data_type,
  is_nullable,
  column_default,
  comment
FROM helios_catalog.information_schema.columns
WHERE table_schema = 'platform'
  AND table_name = 'users'
  AND column_name IN (
    'phone_number',
    'staff_id',
    'designation',
    'must_change_password'
  )
ORDER BY ordinal_position;
