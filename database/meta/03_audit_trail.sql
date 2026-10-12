-- =====================================================================
-- Helios Meta Layer: Administrative and Operational Audit Trail
-- Safe, re-runnable DDL creating meta.audit_trail
-- =====================================================================

USE CATALOG helios;
USE SCHEMA meta;

CREATE TABLE IF NOT EXISTS helios.meta.audit_trail (
  audit_id BIGINT GENERATED ALWAYS AS IDENTITY,
  occurred_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Audit event occurrence timestamp',
  actor_user_id BIGINT COMMENT 'Foreign key to platform.users for actor triggering event',
  actor_role STRING COMMENT 'Role of actor: admin, team_member, smb_owner, system',
  action STRING NOT NULL COMMENT 'Audited action descriptor (e.g. upload_approved, upload_rejected, run_cancelled)',
  tenant_id BIGINT COMMENT 'Foreign key to platform.tenants associated with action',
  batch_id STRING COMMENT 'Optional pipeline execution batch UUID',
  reason STRING COMMENT 'User-provided justification or system reason for action',
  details_json STRING COMMENT 'JSON string containing event payload, metadata, or state diffs',
  CONSTRAINT pk_audit_trail PRIMARY KEY (audit_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Immutable audit trail capturing administrative, review, and pipeline operational actions';
