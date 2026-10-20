USE CATALOG helios_catalog;

USE SCHEMA platform;

MERGE INTO helios_catalog.platform.tenants AS target
USING (
  SELECT 
    'Apex Consumer Goods' AS business_name,
    'Apparel & Footwear' AS industry,
    'owner@apexconsumer.com' AS contact_email,
    true AS is_active
) AS source
ON target.contact_email = source.contact_email
WHEN MATCHED THEN
  UPDATE SET 
    business_name = source.business_name,
    industry = source.industry,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (business_name, industry, contact_email, is_active)
  VALUES (source.business_name, source.industry, source.contact_email, source.is_active);

MERGE INTO helios_catalog.platform.tenants AS target
USING (
  SELECT 
    'Pacific Tech & Corporate' AS business_name,
    'Consumer Electronics' AS industry,
    'owner@pacifictech.com' AS contact_email,
    true AS is_active
) AS source
ON target.contact_email = source.contact_email
WHEN MATCHED THEN
  UPDATE SET 
    business_name = source.business_name,
    industry = source.industry,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (business_name, industry, contact_email, is_active)
  VALUES (source.business_name, source.industry, source.contact_email, source.is_active);

MERGE INTO helios_catalog.platform.tenants AS target
USING (
  SELECT 
    'Vanguard Home Office' AS business_name,
    'Office Supplies & Furniture' AS industry,
    'owner@vanguardhome.com' AS contact_email,
    true AS is_active
) AS source
ON target.contact_email = source.contact_email
WHEN MATCHED THEN
  UPDATE SET 
    business_name = source.business_name,
    industry = source.industry,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (business_name, industry, contact_email, is_active)
  VALUES (source.business_name, source.industry, source.contact_email, source.is_active);

MERGE INTO helios_catalog.platform.users AS target
USING (
  SELECT 
    'admin@helios.io' AS email,
    'Helios Admin' AS name,
    '$2b$12$ggFEq1DrWKiPJwPJFgCwLuEJgA0PjNCYBYSCKK5HDgWsDo0DSlE.y' AS password_hash,
    'admin' AS role,
    CAST(NULL AS BIGINT) AS tenant_id,
    true AS is_active
  FROM (SELECT 1) _dummy
  
) AS source
ON target.email = source.email
WHEN MATCHED THEN
  UPDATE SET 
    name = source.name,
    password_hash = source.password_hash,
    role = source.role,
    tenant_id = source.tenant_id,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (name, email, password_hash, role, tenant_id, is_active)
  VALUES (source.name, source.email, source.password_hash, source.role, source.tenant_id, source.is_active);

MERGE INTO helios_catalog.platform.users AS target
USING (
  SELECT 
    'team@helios.io' AS email,
    'Sarah Jenkins' AS name,
    '$2b$12$ggFEq1DrWKiPJwPJFgCwLuEJgA0PjNCYBYSCKK5HDgWsDo0DSlE.y' AS password_hash,
    'team_member' AS role,
    CAST(NULL AS BIGINT) AS tenant_id,
    true AS is_active
  FROM (SELECT 1) _dummy
  
) AS source
ON target.email = source.email
WHEN MATCHED THEN
  UPDATE SET 
    name = source.name,
    password_hash = source.password_hash,
    role = source.role,
    tenant_id = source.tenant_id,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (name, email, password_hash, role, tenant_id, is_active)
  VALUES (source.name, source.email, source.password_hash, source.role, source.tenant_id, source.is_active);

MERGE INTO helios_catalog.platform.users AS target
USING (
  SELECT 
    'owner@apexconsumer.com' AS email,
    'Marcus Vance' AS name,
    '$2b$12$ggFEq1DrWKiPJwPJFgCwLuEJgA0PjNCYBYSCKK5HDgWsDo0DSlE.y' AS password_hash,
    'smb_owner' AS role,
    t.tenant_id,
    true AS is_active
  FROM (SELECT 1) _dummy
  INNER JOIN helios_catalog.platform.tenants t ON t.contact_email = 'owner@apexconsumer.com'
) AS source
ON target.email = source.email
WHEN MATCHED THEN
  UPDATE SET 
    name = source.name,
    password_hash = source.password_hash,
    role = source.role,
    tenant_id = source.tenant_id,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (name, email, password_hash, role, tenant_id, is_active)
  VALUES (source.name, source.email, source.password_hash, source.role, source.tenant_id, source.is_active);

MERGE INTO helios_catalog.platform.users AS target
USING (
  SELECT 
    'owner@pacifictech.com' AS email,
    'Elena Rostova' AS name,
    '$2b$12$ggFEq1DrWKiPJwPJFgCwLuEJgA0PjNCYBYSCKK5HDgWsDo0DSlE.y' AS password_hash,
    'smb_owner' AS role,
    t.tenant_id,
    true AS is_active
  FROM (SELECT 1) _dummy
  INNER JOIN helios_catalog.platform.tenants t ON t.contact_email = 'owner@pacifictech.com'
) AS source
ON target.email = source.email
WHEN MATCHED THEN
  UPDATE SET 
    name = source.name,
    password_hash = source.password_hash,
    role = source.role,
    tenant_id = source.tenant_id,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (name, email, password_hash, role, tenant_id, is_active)
  VALUES (source.name, source.email, source.password_hash, source.role, source.tenant_id, source.is_active);

MERGE INTO helios_catalog.platform.users AS target
USING (
  SELECT 
    'owner@vanguardhome.com' AS email,
    'David Kim' AS name,
    '$2b$12$ggFEq1DrWKiPJwPJFgCwLuEJgA0PjNCYBYSCKK5HDgWsDo0DSlE.y' AS password_hash,
    'smb_owner' AS role,
    t.tenant_id,
    true AS is_active
  FROM (SELECT 1) _dummy
  INNER JOIN helios_catalog.platform.tenants t ON t.contact_email = 'owner@vanguardhome.com'
) AS source
ON target.email = source.email
WHEN MATCHED THEN
  UPDATE SET 
    name = source.name,
    password_hash = source.password_hash,
    role = source.role,
    tenant_id = source.tenant_id,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (name, email, password_hash, role, tenant_id, is_active)
  VALUES (source.name, source.email, source.password_hash, source.role, source.tenant_id, source.is_active);

MERGE INTO helios_catalog.platform.team_assignments AS target
USING (
  SELECT u.user_id, t.tenant_id
  FROM helios_catalog.platform.users u
  CROSS JOIN (
    SELECT tenant_id FROM helios_catalog.platform.tenants 
    WHERE contact_email IN ('owner@apexconsumer.com', 'owner@pacifictech.com')
  ) t
  WHERE u.email = 'team@helios.io'
) AS source
ON target.user_id = source.user_id AND target.tenant_id = source.tenant_id
WHEN NOT MATCHED THEN
  INSERT (user_id, tenant_id)
  VALUES (source.user_id, source.tenant_id);

MERGE INTO helios_catalog.platform.db_connections AS target
USING (
  SELECT 
    t.tenant_id,
    'postgresql' AS db_type,
    'demo-pg.helios.internal' AS host,
    5432 AS port,
    'pacific_ecom_prod' AS database_name,
    'helios_sync_user' AS username,
    'helios_tenant_2:helios-tenant-2-conn-demo1' AS encrypted_credential_ref,
    'SELECT * FROM daily_transactions WHERE status = ''COMPLETED''' AS table_or_query,
    true AS is_active
  FROM helios_catalog.platform.tenants t
  WHERE t.contact_email = 'owner@pacifictech.com'
) AS source
ON target.tenant_id = source.tenant_id AND target.encrypted_credential_ref = source.encrypted_credential_ref
WHEN MATCHED THEN
  UPDATE SET 
    db_type = source.db_type,
    host = source.host,
    port = source.port,
    database_name = source.database_name,
    username = source.username,
    table_or_query = source.table_or_query,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (tenant_id, db_type, host, port, database_name, username, encrypted_credential_ref, table_or_query, is_active)
  VALUES (source.tenant_id, source.db_type, source.host, source.port, source.database_name, source.username, source.encrypted_credential_ref, source.table_or_query, source.is_active);

MERGE INTO helios_catalog.platform.api_keys AS target
USING (
  SELECT 
    t.tenant_id,
    '3837fdf31054d3137cabe83084aa3a12ac62864398667bfd444c451a3982272c' AS key_hash,
    'helios_live_••••2026' AS key_prefix,
    true AS is_active
  FROM helios_catalog.platform.tenants t
  WHERE t.contact_email = 'owner@vanguardhome.com'
) AS source
ON target.tenant_id = source.tenant_id AND target.key_prefix = source.key_prefix
WHEN MATCHED THEN
  UPDATE SET 
    key_hash = source.key_hash,
    is_active = source.is_active
WHEN NOT MATCHED THEN
  INSERT (tenant_id, key_hash, key_prefix, is_active)
  VALUES (source.tenant_id, source.key_hash, source.key_prefix, source.is_active);
