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
COMMENT 'Transforms validated Silver orders into gold.fact_orders via MERGE on (tenant_id, source_order_line_key)'
AS BEGIN
    MERGE INTO helios.gold.fact_orders AS target
    USING (
        SELECT
            s.tenant_id,
            coalesce(p.product_id, 0) AS product_id,
            coalesce(c.customer_id, 0) AS customer_id,
            coalesce(d.date_id, cast(date_format(s.order_date, 'yyyyMMdd') AS bigint)) AS date_id,
            coalesce(s.quantity, 1) AS quantity,
            coalesce(s.unit_price, 0.0000) AS unit_price,
            coalesce(s.discount, 0.0000) AS discount,
            coalesce(s.total, 0.0000) AS total,
            -- Calculate gross profit contribution (uses actual profit from silver, or fallback 30% baseline)
            coalesce(s.profit, round(coalesce(s.total, 0.0000) * 0.30, 4)) AS profit,
            s.order_id AS source_order_id,
            CASE 
                WHEN s.product_id IS NOT NULL AND trim(s.product_id) != '' 
                THEN concat(s.order_id, '_', s.product_id)
                ELSE s.order_id 
            END AS source_order_line_key,
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
          AND s.is_valid = true
        QUALIFY row_number() OVER (
            PARTITION BY s.tenant_id, 
                         CASE 
                             WHEN s.product_id IS NOT NULL AND trim(s.product_id) != '' 
                             THEN concat(s.order_id, '_', s.product_id)
                             ELSE s.order_id 
                         END
            ORDER BY s.processed_at DESC
        ) = 1
    ) AS source
    ON target.tenant_id = source.tenant_id
   AND target.source_order_line_key = source.source_order_line_key
    WHEN MATCHED THEN
        UPDATE SET
            target.product_id = source.product_id,
            target.customer_id = source.customer_id,
            target.date_id = source.date_id,
            target.quantity = source.quantity,
            target.unit_price = source.unit_price,
            target.discount = source.discount,
            target.total = source.total,
            target.profit = source.profit,
            target.source_order_id = source.source_order_id,
            target.batch_id = source.batch_id,
            target.created_at = source.created_at
    WHEN NOT MATCHED THEN
        INSERT (
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
            source_order_line_key,
            batch_id,
            created_at
        )
        VALUES (
            source.tenant_id,
            source.product_id,
            source.customer_id,
            source.date_id,
            source.quantity,
            source.unit_price,
            source.discount,
            source.total,
            source.profit,
            source.source_order_id,
            source.source_order_line_key,
            source.batch_id,
            source.created_at
        );
END;
