-- =====================================================================
-- Helios Platform Layer: Managed Database Connections
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

CREATE TABLE IF NOT EXISTS helios.platform.db_connections (
  connection_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tenant_id BIGINT NOT NULL COMMENT 'Foreign key to platform.tenants representing the tenant owner',
  db_type STRING NOT NULL COMMENT 'Target RDBMS engine type: mysql, postgresql, or sqlserver',
  host STRING NOT NULL COMMENT 'Database server hostname or IP address',
  port INT NOT NULL COMMENT 'Database listener port number',
  database_name STRING NOT NULL COMMENT 'Target database/catalog name',
  username STRING NOT NULL COMMENT 'Database service user identifier',
  encrypted_credential_ref STRING NOT NULL COMMENT 'Reference key into Databricks Secrets (e.g. scope:key). NEVER store raw passwords',
  table_or_query STRING NOT NULL COMMENT 'Table name, view name, or custom SELECT query to extract',
  last_synced_at TIMESTAMP COMMENT 'Timestamp of last successful data extraction sync',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Creation timestamp of connection configuration',
  is_active BOOLEAN NOT NULL DEFAULT true COMMENT 'Flag controlling whether scheduled connector sync is active',
  CONSTRAINT pk_db_connections PRIMARY KEY (connection_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Managed database connector definitions storing connection parameters and Databricks Secret references (db_type: mysql, postgresql, sqlserver)';
