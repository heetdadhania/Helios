-- =====================================================================
-- Helios Gold Layer Stored Procedure: Refresh Daily Summary Fact
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE OR REPLACE PROCEDURE helios.gold.sp_refresh_daily_summary (
    IN tenant_id_param BIGINT,
    IN batch_id_param STRING
)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Recalculates pre-aggregated daily sales and KPI summaries for dates affected by the batch from fact_orders'
AS BEGIN
    MERGE INTO helios.gold.fact_orders_daily_summary AS target
    USING (
        WITH affected_dates AS (
            SELECT DISTINCT date_id
            FROM helios.gold.fact_orders
            WHERE tenant_id = tenant_id_param 
              AND batch_id = batch_id_param
            UNION
            SELECT DISTINCT cast(date_format(s.order_date, 'yyyyMMdd') AS bigint) AS date_id
            FROM helios.silver.orders_clean s
            WHERE s.tenant_id = tenant_id_param
              AND s.batch_id = batch_id_param
              AND s.is_valid = true
        ),
        daily_rollups AS (
            SELECT
                fo.tenant_id,
                fo.date_id,
                count(DISTINCT fo.source_order_id) AS total_orders,
                round(sum(coalesce(fo.total, 0.0000)), 4) AS total_revenue,
                CASE 
                    WHEN count(DISTINCT fo.source_order_id) > 0 
                    THEN round(sum(coalesce(fo.total, 0.0000)) / count(DISTINCT fo.source_order_id), 4)
                    ELSE 0.0000 
                END AS avg_order_value,
                sum(coalesce(fo.quantity, 0)) AS total_quantity
            FROM helios.gold.fact_orders fo
            INNER JOIN affected_dates ad
              ON fo.date_id = ad.date_id
            WHERE fo.tenant_id = tenant_id_param
            GROUP BY fo.tenant_id, fo.date_id
        )
        SELECT * FROM daily_rollups
    ) AS source
    ON target.tenant_id = source.tenant_id
   AND target.date_id = source.date_id
    WHEN MATCHED THEN
        UPDATE SET
            target.total_orders = source.total_orders,
            target.total_revenue = source.total_revenue,
            target.avg_order_value = source.avg_order_value,
            target.total_quantity = source.total_quantity,
            target.updated_at = current_timestamp()
    WHEN NOT MATCHED THEN
        INSERT (tenant_id, date_id, total_orders, total_revenue, avg_order_value, total_quantity, updated_at)
        VALUES (
            source.tenant_id,
            source.date_id,
            source.total_orders,
            source.total_revenue,
            source.avg_order_value,
            source.total_quantity,
            current_timestamp()
        );
END;
