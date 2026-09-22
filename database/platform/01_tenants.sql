-- =====================================================================
-- Helios Platform Layer: Tenants Registry
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

CREATE TABLE IF NOT EXISTS helios.platform.tenants (
  tenant_id BIGINT GENERATED ALWAYS AS IDENTITY,
  business_name STRING NOT NULL COMMENT 'Legal or trading name of the customer business/organization',
  industry STRING COMMENT 'Industry vertical (e.g., Apparel, Electronics, Health & Beauty)',
  contact_email STRING NOT NULL COMMENT 'Primary administrative point-of-contact email address',
  created_by BIGINT COMMENT 'Reference to user_id of Admin or Team Member who provisioned this tenant',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when tenant was onboarded',
  is_active BOOLEAN NOT NULL DEFAULT true COMMENT 'Flag indicating if tenant subscription and access is active',
  CONSTRAINT pk_tenants PRIMARY KEY (tenant_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Tenant directory tracking organizations onboarded onto the Helios platform';
