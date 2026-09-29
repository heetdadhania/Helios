-- =====================================================================
-- Helios Platform Layer Migration: Add message_source to support_messages
-- =====================================================================

USE CATALOG helios;
USE SCHEMA platform;

ALTER TABLE helios.platform.support_messages 
ADD COLUMN IF NOT EXISTS message_source STRING DEFAULT 'smb_owner'
COMMENT 'Source role of message sender: smb_owner or team_member';
