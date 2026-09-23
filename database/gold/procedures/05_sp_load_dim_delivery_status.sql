-- =====================================================================
-- Helios Gold Layer Stored Procedure: Load Delivery Status Dimension
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE OR REPLACE PROCEDURE helios.gold.sp_load_dim_delivery_status (
    IN tenant_id_param BIGINT,
    IN batch_id_param STRING
)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Merges distinct delivery statuses from Silver shipping into gold.dim_delivery_status'
AS BEGIN
    MERGE INTO helios.gold.dim_delivery_status AS target
    USING (
        SELECT DISTINCT 
            coalesce(trim(delivery_status), 'Unknown') AS status_name,
            CASE 
                WHEN lower(trim(delivery_status)) IN ('delivered', 'returned', 'cancelled') THEN true
                ELSE false 
            END AS is_terminal
        FROM helios.silver.shipping_clean
        WHERE tenant_id = tenant_id_param 
          AND batch_id = batch_id_param 
          AND is_valid = true 
          AND delivery_status IS NOT NULL 
          AND trim(delivery_status) <> ''
    ) AS source
    ON lower(target.status_name) = lower(source.status_name)
    WHEN MATCHED AND target.is_terminal <> source.is_terminal THEN
        UPDATE SET target.is_terminal = source.is_terminal
    WHEN NOT MATCHED THEN
        INSERT (status_name, is_terminal)
        VALUES (source.status_name, source.is_terminal);
END;
