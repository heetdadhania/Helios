-- =====================================================================
-- Helios Runtime Data Reset SQL
-- Cleans runtime and transactional state while preserving configuration.
-- =====================================================================

-- 1. Metadata and Logs
DELETE FROM `helios_catalog`.`meta`.`data_quality_log`;
DELETE FROM `helios_catalog`.`meta`.`etl_audit_log`;
DELETE FROM `helios_catalog`.`meta`.`audit_trail`;

-- 2. Platform Runtime Tracking
DELETE FROM `helios_catalog`.`platform`.`support_messages`;
DELETE FROM `helios_catalog`.`platform`.`notification_log`;
DELETE FROM `helios_catalog`.`platform`.`inferred_schema`;
DELETE FROM `helios_catalog`.`platform`.`pipeline_status`;
DELETE FROM `helios_catalog`.`platform`.`pending_uploads`;

-- 3. Bronze Tables
DELETE FROM `helios_catalog`.`bronze`.`raw_orders`;
DELETE FROM `helios_catalog`.`bronze`.`raw_shipping`;

-- 4. Silver Tables
DELETE FROM `helios_catalog`.`silver`.`orders_clean`;
DELETE FROM `helios_catalog`.`silver`.`shipping_clean`;

-- 5. Gold Fact and Dynamic Dimension Tables
DELETE FROM `helios_catalog`.`gold`.`fact_orders_daily_summary`;
DELETE FROM `helios_catalog`.`gold`.`fact_shipments`;
DELETE FROM `helios_catalog`.`gold`.`fact_orders`;
DELETE FROM `helios_catalog`.`gold`.`dim_product`;
DELETE FROM `helios_catalog`.`gold`.`dim_customer`;
