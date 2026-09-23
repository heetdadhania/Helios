-- =====================================================================
-- Helios Gold Layer Stored Procedure: Load Customer Dimension
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE OR REPLACE PROCEDURE helios.gold.sp_load_dim_customer (
    IN tenant_id_param BIGINT,
    IN batch_id_param STRING
)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Performs tenant-scoped upsert of distinct customers from Silver orders into gold.dim_customer'
AS BEGIN
    MERGE INTO helios.gold.dim_customer AS target
    USING (
        SELECT 
            tenant_id,
            CASE 
                WHEN customer_id LIKE '%@%' THEN split(customer_id, '@')[0]
                ELSE customer_id 
            END AS customer_name,
            'Standard' AS segment,
            CASE 
                WHEN customer_id LIKE '%@%' THEN lower(trim(customer_id))
                ELSE NULL 
            END AS email,
            customer_id AS source_customer_ref
        FROM (
            SELECT DISTINCT 
                tenant_id, 
                customer_id
            FROM helios.silver.orders_clean
            WHERE tenant_id = tenant_id_param 
              AND batch_id = batch_id_param 
              AND is_valid = true 
              AND customer_id IS NOT NULL 
              AND trim(customer_id) <> ''
        )
    ) AS source
    ON target.tenant_id = source.tenant_id 
   AND (
        (source.email IS NOT NULL AND target.email = source.email)
        OR (target.customer_name = source.source_customer_ref)
   )
    WHEN MATCHED AND (target.customer_name <> source.customer_name OR (target.email IS NULL AND source.email IS NOT NULL)) THEN
        UPDATE SET 
            target.customer_name = coalesce(source.customer_name, target.customer_name),
            target.email = coalesce(source.email, target.email),
            target.updated_at = current_timestamp()
    WHEN NOT MATCHED THEN
        INSERT (tenant_id, customer_name, segment, email, created_at, updated_at)
        VALUES (source.tenant_id, source.customer_name, source.segment, source.email, current_timestamp(), current_timestamp());
END;
