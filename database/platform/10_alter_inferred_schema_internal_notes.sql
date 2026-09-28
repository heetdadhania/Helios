-- =====================================================================
-- Helios Platform Layer Migration: Add internal_notes to inferred_schema
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

ALTER TABLE helios.platform.inferred_schema 
ADD COLUMN IF NOT EXISTS internal_notes STRING 
COMMENT 'Optional internal reviewer notes recorded during schema confirmation';
