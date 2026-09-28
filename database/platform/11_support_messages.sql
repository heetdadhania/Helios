-- =====================================================================
-- Helios Platform Layer: Support Messages & Update Requests
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

CREATE TABLE IF NOT EXISTS helios.platform.support_messages (
  message_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing the tenant context',
  from_user_id BIGINT NOT NULL COMMENT 'Foreign key to platform.users for the sender (SMB Owner)',
  to_user_id BIGINT NOT NULL COMMENT 'Foreign key to platform.users for the routed recipient (Team Member or fallback Admin)',
  message STRING NOT NULL COMMENT 'Content of the support or status update request',
  status STRING NOT NULL DEFAULT 'open' COMMENT 'Resolution state: open, resolved',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when the message was sent',
  resolved_at TIMESTAMP COMMENT 'Timestamp when the message was marked resolved',
  CONSTRAINT pk_support_messages PRIMARY KEY (message_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Contact and request update messages between SMB Owners and assigned Team Members or Admins';
