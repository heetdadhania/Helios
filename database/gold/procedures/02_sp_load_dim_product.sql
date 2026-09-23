-- =====================================================================
-- Helios Gold Layer Stored Procedure: Load Product Dimension
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE OR REPLACE PROCEDURE helios.gold.sp_load_dim_product (
    IN tenant_id_param BIGINT,
    IN batch_id_param STRING
)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Performs tenant-scoped upsert of distinct products from Silver orders into gold.dim_product'
AS BEGIN
    MERGE INTO helios.gold.dim_product AS target
    USING (
        SELECT 
            tenant_id,
            product_id AS source_product_ref,
            -- Provide default label if product reference is minimal
            coalesce(product_id, 'UNKNOWN_SKU') AS product_name,
            'General' AS category
        FROM (
            SELECT DISTINCT 
                tenant_id, 
                product_id
            FROM helios.silver.orders_clean
            WHERE tenant_id = tenant_id_param 
              AND batch_id = batch_id_param 
              AND is_valid = true 
              AND product_id IS NOT NULL 
              AND trim(product_id) <> ''
        )
    ) AS source
    ON target.tenant_id = source.tenant_id 
   AND target.source_product_ref = source.source_product_ref
    WHEN MATCHED AND (target.product_name <> source.product_name OR target.product_name IS NULL) THEN
        UPDATE SET 
            target.product_name = source.product_name,
            target.updated_at = current_timestamp()
    WHEN NOT MATCHED THEN
        INSERT (tenant_id, product_name, category, source_product_ref, created_at, updated_at)
        VALUES (source.tenant_id, source.product_name, source.category, source.source_product_ref, current_timestamp(), current_timestamp());
END;
