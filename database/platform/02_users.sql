-- =====================================================================
-- Helios Platform Layer: Users & RBAC
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

CREATE TABLE IF NOT EXISTS helios.platform.users (
  user_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT COMMENT 'Foreign key to platform.tenants (NULL for global Admin users)',
  name STRING NOT NULL COMMENT 'Full display name of the user',
  email STRING NOT NULL COMMENT 'Unique user email address for portal authentication',
  password_hash STRING NOT NULL COMMENT 'Bcrypt-hashed password string',
  role STRING NOT NULL COMMENT 'Role-based access level: smb_owner, team_member, admin',
  is_active BOOLEAN NOT NULL DEFAULT true COMMENT 'Flag indicating if user account is currently permitted to log in',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Account registration timestamp',
  CONSTRAINT pk_users PRIMARY KEY (user_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'User accounts with credentials and role-based permissions (roles: smb_owner, team_member, admin)';
