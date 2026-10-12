-- Databricks notebook source
-- =====================================================================
-- Helios Platform: Master Schema Deployment Notebook
-- Executes all Medallion and Platform DDL scripts in dependency order
-- =====================================================================

-- COMMAND ----------
-- 1. Setup Catalog and Schemas
%run ./00_catalog_setup

-- COMMAND ----------
-- 2. Platform Layer Tables (Registry, Auth, Ingestion State)
%run ./platform/01_tenants
%run ./platform/02_users
%run ./platform/03_team_assignments
%run ./platform/04_pending_uploads
%run ./platform/05_db_connections
%run ./platform/06_api_keys
%run ./platform/07_pipeline_status
%run ./platform/08_inferred_schema
%run ./platform/09_notification_log
%run ./platform/10_alter_inferred_schema_internal_notes
%run ./platform/11_support_messages
%run ./platform/12_alter_support_messages_message_source
%run ./platform/13_alter_tenants_details
%run ./platform/14_alter_users_staff_details
%run ./platform/15_alter_users_security
%run ./platform/16_alter_pending_uploads_review
%run ./platform/17_alter_pipeline_status_lifecycle
%run ./platform/row_filters

-- COMMAND ----------
-- 3. Meta Layer Tables (Audit & Data Quality Logs)
%run ./meta/01_etl_audit_log
%run ./meta/02_data_quality_log
%run ./meta/03_audit_trail

-- COMMAND ----------
-- 4. Bronze Layer Tables (Raw Landing Zone)
%run ./bronze/01_raw_orders
%run ./bronze/02_raw_shipping

-- COMMAND ----------
-- 5. Silver Layer Tables (Cleaned & Validated Domain Data)
%run ./silver/01_orders_clean
%run ./silver/02_shipping_clean

-- COMMAND ----------
-- 6. Gold Layer Tables (Star Schema Dimensions, Facts & Aggregates)
%run ./gold/01_dim_date
%run ./gold/02_dim_product
%run ./gold/03_dim_customer
%run ./gold/04_dim_shipping_mode
%run ./gold/05_dim_delivery_status
%run ./gold/06_fact_orders
%run ./gold/07_fact_shipments
%run ./gold/08_fact_orders_daily_summary

-- COMMAND ----------
-- 7. Verification Query
SELECT 'Catalog' AS object_type, catalog_name AS name FROM system.information_schema.catalogs WHERE catalog_name = 'helios'
UNION ALL
SELECT 'Schema' AS object_type, schema_name AS name FROM helios.information_schema.schemata;
