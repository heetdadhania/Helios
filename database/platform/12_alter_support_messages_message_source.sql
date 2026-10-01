-- =====================================================================
-- Helios Platform Layer Migration: Add message_source to support_messages
-- =====================================================================

USE CATALOG helios_catalog;
USE SCHEMA platform;

ALTER TABLE helios_catalog.platform.support_messages 
ADD COLUMN IF NOT EXISTS message_source STRING DEFAULT 'smb_owner'
COMMENT 'Source role of message sender: smb_owner or team_member';
