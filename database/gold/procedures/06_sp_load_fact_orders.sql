-- =====================================================================
-- Helios Gold Layer Stored Procedure: Load Orders Fact Table
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE OR REPLACE PROCEDURE helios.gold.sp_load_fact_orders (
    IN tenant_id_param BIGINT,
    IN batch_id_param STRING
)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Transforms validated Silver orders into gold.fact_orders joining dimensions for surrogate keys'
AS BEGIN
    -- Ensure idempotent loading by removing prior attempts for this batch
    DELETE FROM helios.gold.fact_orders
    WHERE tenant_id = tenant_id_param 
      AND batch_id = batch_id_param;

    -- Insert cleansed records joined to dimension surrogate keys
    INSERT INTO helios.gold.fact_orders (
        tenant_id,
        product_id,
        customer_id,
        date_id,
        quantity,
        unit_price,
        discount,
        total,
        profit,
        source_order_id,
        batch_id,
        created_at
    )
    SELECT
        s.tenant_id,
        coalesce(p.product_id, 0) AS product_id,
        coalesce(c.customer_id, 0) AS customer_id,
        coalesce(d.date_id, cast(date_format(s.order_date, 'yyyyMMdd') AS bigint)) AS date_id,
        coalesce(s.quantity, 1) AS quantity,
        coalesce(s.unit_price, 0.0000) AS unit_price,
        coalesce(s.discount, 0.0000) AS discount,
        coalesce(s.total, 0.0000) AS total,
        -- Calculate gross profit estimation (30% margin baseline or net after discount)
        round(coalesce(s.total, 0.0000) * 0.30, 4) AS profit,
        s.order_id AS source_order_id,
        s.batch_id,
        current_timestamp() AS created_at
    FROM helios.silver.orders_clean s
    LEFT JOIN helios.gold.dim_product p
      ON p.tenant_id = s.tenant_id
     AND p.source_product_ref = s.product_id
    LEFT JOIN helios.gold.dim_customer c
      ON c.tenant_id = s.tenant_id
     AND (
          (s.customer_id LIKE '%@%' AND c.email = lower(trim(s.customer_id)))
          OR c.customer_name = s.customer_id
     )
    LEFT JOIN helios.gold.dim_date d
      ON d.date_id = cast(date_format(s.order_date, 'yyyyMMdd') AS bigint)
    WHERE s.tenant_id = tenant_id_param
      AND s.batch_id = batch_id_param
      AND s.is_valid = true;
END;
