-- =====================================================================
-- Helios Gold Layer Stored Procedure: Load Shipping Mode Dimension
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE OR REPLACE PROCEDURE helios.gold.sp_load_dim_shipping_mode (
    IN tenant_id_param BIGINT,
    IN batch_id_param STRING
)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Merges distinct fulfillment shipping modes from Silver shipping into gold.dim_shipping_mode'
AS BEGIN
    MERGE INTO helios.gold.dim_shipping_mode AS target
    USING (
        SELECT DISTINCT 
            coalesce(trim(shipping_mode), 'Standard') AS mode_name,
            concat('Logistics fulfillment channel: ', coalesce(trim(shipping_mode), 'Standard')) AS description
        FROM helios.silver.shipping_clean
        WHERE tenant_id = tenant_id_param 
          AND batch_id = batch_id_param 
          AND is_valid = true 
          AND shipping_mode IS NOT NULL 
          AND trim(shipping_mode) <> ''
    ) AS source
    ON lower(target.mode_name) = lower(source.mode_name)
    WHEN NOT MATCHED THEN
        INSERT (mode_name, description)
        VALUES (source.mode_name, source.description);
END;
