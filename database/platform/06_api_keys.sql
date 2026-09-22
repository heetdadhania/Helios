-- =====================================================================
-- Helios Platform Layer: Tenant API Keys
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

CREATE TABLE IF NOT EXISTS helios.platform.api_keys (
  api_key_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing the owning organization',
  key_hash STRING NOT NULL COMMENT 'Cryptographic one-way hash (SHA-256 or bcrypt) of the tenant API key. NEVER store raw keys',
  key_prefix STRING COMMENT 'First 8 characters of key for display and identification purposes (e.g. hls_live_...)',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when API key was issued',
  last_used_at TIMESTAMP COMMENT 'Timestamp of last authenticated API request made with this key',
  is_active BOOLEAN NOT NULL DEFAULT true COMMENT 'Flag indicating if API key is active or revoked',
  CONSTRAINT pk_api_keys PRIMARY KEY (api_key_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Hashed API keys for authenticating programmatic tenant ingestion requests';
