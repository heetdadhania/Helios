-- =====================================================================
-- Helios Platform Layer Migration: Add User Security & Lockout Columns
-- Safe, re-runnable DDL script adding security and lockout tracking columns
-- to platform.users.
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

-- 1. Ensure table properties support column defaults
ALTER TABLE helios.platform.users SET TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported');

-- 2. Add security columns only if not already present
BEGIN
  -- last_login_at (TIMESTAMP)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'users' AND column_name = 'last_login_at') = 0 THEN
    ALTER TABLE helios.platform.users ADD COLUMNS (
      last_login_at TIMESTAMP COMMENT 'Timestamp of last successful user authentication'
    );
  END IF;

  -- failed_login_count (INT default 0)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'users' AND column_name = 'failed_login_count') = 0 THEN
    ALTER TABLE helios.platform.users ADD COLUMNS (
      failed_login_count INT COMMENT 'Count of consecutive failed login attempts'
    );
    ALTER TABLE helios.platform.users ALTER COLUMN failed_login_count SET DEFAULT 0;
  END IF;

  -- locked_until (TIMESTAMP)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'users' AND column_name = 'locked_until') = 0 THEN
    ALTER TABLE helios.platform.users ADD COLUMNS (
      locked_until TIMESTAMP COMMENT 'Timestamp until which user account is locked due to repeated failed logins'
    );
  END IF;

  -- password_changed_at (TIMESTAMP)
  IF (SELECT count(*) FROM helios.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'users' AND column_name = 'password_changed_at') = 0 THEN
    ALTER TABLE helios.platform.users ADD COLUMNS (
      password_changed_at TIMESTAMP COMMENT 'Timestamp of most recent password modification'
    );
  END IF;
END;

-- 3. Backfill default failed_login_count for existing user rows
UPDATE helios.platform.users SET failed_login_count = 0 WHERE failed_login_count IS NULL;
