-- =====================================================================
-- Helios Platform Layer: Inferred Schema Registry
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

CREATE TABLE IF NOT EXISTS helios.platform.inferred_schema (
  inference_id BIGINT GENERATED ALWAYS AS IDENTITY,
  batch_id STRING NOT NULL COMMENT 'Foreign key to platform.pipeline_status batch UUID',
  detected_template STRING COMMENT 'Identified standard schema pattern (shopify_orders, stripe_charges, custom)',
  column_mapping_json STRING NOT NULL COMMENT 'JSON string describing source-to-silver column mapping definitions and inferred types',
  confidence_score DOUBLE COMMENT 'Model or heuristic confidence rating (0.0 to 1.0) for schema classification',
  confirmed_by BIGINT COMMENT 'Foreign key to platform.users who reviewed and approved the inferred schema',
  confirmed_at TIMESTAMP COMMENT 'Timestamp when mapping was confirmed by user or automated rule',
  created_at TIMESTAMP NOT NULL DEFAULT current_timestamp() COMMENT 'Timestamp when schema inference was executed',
  CONSTRAINT pk_inferred_schema PRIMARY KEY (inference_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.feature.allowColumnDefaults' = 'supported',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Stores AI and rule-inferred schemas and user mapping confirmations for raw ingested batches';
