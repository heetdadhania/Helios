-- =====================================================================
-- Helios Gold Layer Stored Procedure: Load Shipments Fact Table
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE OR REPLACE PROCEDURE helios.gold.sp_load_fact_shipments (
    IN tenant_id_param BIGINT,
    IN batch_id_param STRING
)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Transforms validated Silver shipments into gold.fact_shipments via MERGE on (tenant_id, source_order_line_key)'
AS BEGIN
    MERGE INTO helios.gold.fact_shipments AS target
    USING (
        SELECT
            s.tenant_id,
            fo.order_line_id,
            coalesce(sm.shipping_mode_id, 1) AS shipping_mode_id,
            coalesce(ds.delivery_status_id, 1) AS delivery_status_id,
            coalesce(d.date_id, cast(date_format(coalesce(s.actual_date, s.scheduled_date, current_date()), 'yyyyMMdd') AS bigint)) AS date_id,
            coalesce(
                s.shipping_days,
                datediff(s.actual_date, s.scheduled_date),
                0
            ) AS shipping_days,
            coalesce(datediff(s.scheduled_date, coalesce(s.processed_at, current_timestamp())), 3) AS scheduled_days,
            CASE
                WHEN s.actual_date IS NOT NULL AND s.scheduled_date IS NOT NULL AND s.actual_date > s.scheduled_date THEN true
                ELSE false
            END AS late_flag,
            s.order_id AS source_order_id,
            s.order_id AS source_order_line_key,
            s.batch_id,
            current_timestamp() AS created_at
        FROM helios.silver.shipping_clean s
        LEFT JOIN helios.gold.dim_shipping_mode sm
          ON lower(sm.mode_name) = lower(coalesce(trim(s.shipping_mode), 'Standard'))
        LEFT JOIN helios.gold.dim_delivery_status ds
          ON lower(ds.status_name) = lower(coalesce(trim(s.delivery_status), 'Unknown'))
        LEFT JOIN helios.gold.dim_date d
          ON d.date_id = cast(date_format(coalesce(s.actual_date, s.scheduled_date), 'yyyyMMdd') AS bigint)
        LEFT JOIN (
            -- Pick primary matching order line if exists
            SELECT 
                tenant_id, 
                source_order_id, 
                min(order_line_id) AS order_line_id
            FROM helios.gold.fact_orders
            WHERE tenant_id = tenant_id_param
            GROUP BY tenant_id, source_order_id
        ) fo
          ON fo.tenant_id = s.tenant_id
         AND fo.source_order_id = s.order_id
        WHERE s.tenant_id = tenant_id_param
          AND s.batch_id = batch_id_param
          AND s.is_valid = true
        QUALIFY row_number() OVER (
            PARTITION BY s.tenant_id, s.order_id
            ORDER BY s.processed_at DESC
        ) = 1
    ) AS source
    ON target.tenant_id = source.tenant_id
   AND target.source_order_line_key = source.source_order_line_key
    WHEN MATCHED THEN
        UPDATE SET
            target.order_line_id = source.order_line_id,
            target.shipping_mode_id = source.shipping_mode_id,
            target.delivery_status_id = source.delivery_status_id,
            target.date_id = source.date_id,
            target.shipping_days = source.shipping_days,
            target.scheduled_days = source.scheduled_days,
            target.late_flag = source.late_flag,
            target.source_order_id = source.source_order_id,
            target.batch_id = source.batch_id,
            target.created_at = source.created_at
    WHEN NOT MATCHED THEN
        INSERT (
            tenant_id,
            order_line_id,
            shipping_mode_id,
            delivery_status_id,
            date_id,
            shipping_days,
            scheduled_days,
            late_flag,
            source_order_id,
            source_order_line_key,
            batch_id,
            created_at
        )
        VALUES (
            source.tenant_id,
            source.order_line_id,
            source.shipping_mode_id,
            source.delivery_status_id,
            source.date_id,
            source.shipping_days,
            source.scheduled_days,
            source.late_flag,
            source.source_order_id,
            source.source_order_line_key,
            source.batch_id,
            source.created_at
        );
END;
