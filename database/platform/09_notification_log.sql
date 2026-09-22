-- =====================================================================
-- Helios Platform Layer: Notifications Log
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

CREATE TABLE IF NOT EXISTS helios.platform.notification_log (
  notification_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT COMMENT 'Foreign key to platform.tenants (NULL if platform-wide notification)',
  user_id BIGINT COMMENT 'Foreign key to platform.users (NULL if broadcast to all tenant users)',
  message STRING NOT NULL COMMENT 'Notification headline or detailed message body',
  type STRING NOT NULL COMMENT 'Notification category: info, warning, error, approval_required, pipeline_success',
  is_read BOOLEAN NOT NULL DEFAULT false COMMENT 'Flag indicating if recipient user has read this notification',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when notification was generated',
  CONSTRAINT pk_notification_log PRIMARY KEY (notification_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Log of operational alerts, pipeline events, and approval notices delivered to portal users';
