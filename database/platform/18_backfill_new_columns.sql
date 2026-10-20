-- =====================================================================
-- Helios Platform Layer Migration: Backfill New Columns
-- Safe, re-runnable script ensuring default values for boolean and
-- counter columns added in earlier migrations.
-- =====================================================================

USE CATALOG helios_catalog;
USE SCHEMA platform;

-- 1. Backfill platform.users
-- Ensure must_change_password is non-null (default: false)
UPDATE helios_catalog.platform.users 
SET must_change_password = false 
WHERE must_change_password IS NULL;

-- Ensure failed_login_count is non-null (default: 0)
UPDATE helios_catalog.platform.users 
SET failed_login_count = 0 
WHERE failed_login_count IS NULL;

-- Ensure is_active is non-null (default: true)
UPDATE helios_catalog.platform.users 
SET is_active = true 
WHERE is_active IS NULL;

-- 2. Backfill platform.pipeline_status
-- Ensure cancel_requested is non-null (default: false)
UPDATE helios_catalog.platform.pipeline_status 
SET cancel_requested = false 
WHERE cancel_requested IS NULL;

-- 3. Backfill platform.tenants
-- Ensure is_active is non-null (default: true)
UPDATE helios_catalog.platform.tenants 
SET is_active = true 
WHERE is_active IS NULL;
