-- =====================================================================
-- Helios Platform Layer Migration: Add Tenant Details & Contact Info
-- Safe, re-runnable DDL script adding extended tenant metadata columns.
-- Uses information_schema checks inside Databricks compound procedural
-- blocks to ensure safe, idempotent execution even if earlier batches
-- were partially applied.
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
  comment
FROM helios_catalog.information_schema.columns
WHERE table_schema = 'platform'
  AND table_name = 'tenants'
ORDER BY ordinal_position;

-- ---------------------------------------------------------------------
-- 2. Schema Alterations: Add extended tenant columns only if not present
-- ---------------------------------------------------------------------
BEGIN
  -- 1. contact_person_name
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'contact_person_name') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      contact_person_name STRING COMMENT 'Full name of the primary administrative or business contact'
    );
  END IF;

  -- 2. phone_number
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'phone_number') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      phone_number STRING COMMENT 'Primary business phone number'
    );
  END IF;

  -- 3. address_line1
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'address_line1') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      address_line1 STRING COMMENT 'Street address line 1'
    );
  END IF;

  -- 4. address_line2 (nullable)
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'address_line2') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      address_line2 STRING COMMENT 'Suite, unit, floor, or secondary address details (nullable)'
    );
  END IF;

  -- 5. city
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'city') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      city STRING COMMENT 'City or locality of the customer business'
    );
  END IF;

  -- 6. state
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'state') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      state STRING COMMENT 'State, province, or administrative region'
    );
  END IF;

  -- 7. postal_code
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'postal_code') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      postal_code STRING COMMENT 'Postal or ZIP code'
    );
  END IF;

  -- 8. country
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'country') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      country STRING COMMENT 'Country name or standardized country code'
    );
  END IF;

  -- 9. website_url (nullable)
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'website_url') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      website_url STRING COMMENT 'Official company website or eCommerce storefront URL (nullable)'
    );
  END IF;

  -- 10. tax_id (nullable)
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'tax_id') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      tax_id STRING COMMENT 'Tax identification number, EIN, or VAT registration (nullable)'
    );
  END IF;

  -- 11. assigned_team_member_id (nullable)
  IF (SELECT count(*) FROM helios_catalog.information_schema.columns 
      WHERE table_schema = 'platform' AND table_name = 'tenants' AND column_name = 'assigned_team_member_id') = 0 THEN
    ALTER TABLE helios_catalog.platform.tenants ADD COLUMNS (
      assigned_team_member_id BIGINT COMMENT 'Internal team member (platform.users.user_id) assigned to support this tenant (nullable)'
    );
  END IF;
END;

-- ---------------------------------------------------------------------
-- 3. Post-Migration Verification: Verify all 11 columns in information_schema
-- ---------------------------------------------------------------------
SELECT
  column_name,
  data_type,
  is_nullable,
  comment
FROM helios_catalog.information_schema.columns
WHERE table_schema = 'platform'
  AND table_name = 'tenants'
  AND column_name IN (
    'contact_person_name',
    'phone_number',
    'address_line1',
    'address_line2',
    'city',
    'state',
    'postal_code',
    'country',
    'website_url',
    'tax_id',
    'assigned_team_member_id'
  )
ORDER BY ordinal_position;
