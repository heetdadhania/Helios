-- =====================================================================
-- Helios Platform - Catalog and Schema Initialization
-- Unity Catalog Setup for Multi-Tenant Medallion Architecture
-- =====================================================================

-- 1. Create Catalog
-- Creates the top-level Unity Catalog namespace for Helios platform
CREATE CATALOG IF NOT EXISTS helios
COMMENT 'Helios Multi-Tenant Enterprise Data Platform Catalog';

USE CATALOG helios;

-- 2. Create Platform Schema
-- Stores tenant organizations, users, connectors, security, and pipeline state
CREATE SCHEMA IF NOT EXISTS helios.platform
COMMENT 'Platform metadata, tenant registry, authentication, and pipeline orchestration';

-- 3. Create Meta Schema
-- Stores ETL execution audit logs, data quality telemetry, and rejection history
CREATE SCHEMA IF NOT EXISTS helios.meta
COMMENT 'Data quality audit logs, pipeline telemetry, and ingestion monitoring';

-- 4. Create Bronze Layer Schema
-- Stores raw, immutable, append-only ingested payloads
CREATE SCHEMA IF NOT EXISTS helios.bronze
COMMENT 'Raw immutable landing zone for uploads, API pushes, and database streams';

-- 5. Create Silver Layer Schema
-- Stores cleansed, validated, filtered, and conforming domain records
CREATE SCHEMA IF NOT EXISTS helios.silver
COMMENT 'Cleansed, validated, and normalized transactional tables';

-- 6. Create Gold Layer Schema
-- Stores dimensional star-schema models and business intelligence aggregates
CREATE SCHEMA IF NOT EXISTS helios.gold
COMMENT 'Star-schema dimensional models, facts, and business KPI aggregates';
