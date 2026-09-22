-- =====================================================================
-- Helios Gold Layer: Conformed Date Dimension
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE TABLE IF NOT EXISTS helios.gold.dim_date (
  date_id BIGINT NOT NULL COMMENT 'Surrogate date key in YYYYMMDD integer format (e.g. 20260922)',
  full_date DATE NOT NULL COMMENT 'Canonical calendar date value',
  day INT NOT NULL COMMENT 'Day of month (1-31)',
  month INT NOT NULL COMMENT 'Month number (1-12)',
  quarter INT NOT NULL COMMENT 'Calendar quarter (1-4)',
  year INT NOT NULL COMMENT 'Four digit calendar year',
  day_of_week INT NOT NULL COMMENT 'Day of week index (1=Sunday or 1=Monday according to ISO standard)',
  is_weekend BOOLEAN NOT NULL COMMENT 'True if Saturday or Sunday, false otherwise',
  CONSTRAINT pk_dim_date PRIMARY KEY (date_id)
)
USING DELTA
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Conformed calendar date dimension supporting reporting and drill-down across all tenants';
