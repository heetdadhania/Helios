-- =====================================================================
-- Helios Platform Layer: Team Member to Tenant Assignments
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

CREATE TABLE IF NOT EXISTS helios.platform.team_assignments (
  assignment_id BIGINT GENERATED ALWAYS AS IDENTITY,
  user_id BIGINT NOT NULL COMMENT 'Foreign key to platform.users (team_member or admin)',
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants being managed by this user',
  assigned_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when assignment was granted',
  CONSTRAINT pk_team_assignments PRIMARY KEY (assignment_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Associates Helios internal team members with customer tenants they support';
