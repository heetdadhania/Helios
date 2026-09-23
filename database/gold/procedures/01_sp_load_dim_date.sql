-- =====================================================================
-- Helios Gold Layer Stored Procedure: Load Date Dimension
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE OR REPLACE PROCEDURE helios.gold.sp_load_dim_date (
    IN tenant_id_param BIGINT,
    IN batch_id_param STRING
)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Merges distinct transaction dates from Silver orders and shipping into gold.dim_date'
AS BEGIN
    MERGE INTO helios.gold.dim_date AS target
    USING (
        WITH extracted_dates AS (
            SELECT to_date(order_date) AS full_date
            FROM helios.silver.orders_clean
            WHERE tenant_id = tenant_id_param 
              AND batch_id = batch_id_param 
              AND is_valid = true 
              AND order_date IS NOT NULL

            UNION

            SELECT to_date(scheduled_date) AS full_date
            FROM helios.silver.shipping_clean
            WHERE tenant_id = tenant_id_param 
              AND batch_id = batch_id_param 
              AND is_valid = true 
              AND scheduled_date IS NOT NULL

            UNION

            SELECT to_date(actual_date) AS full_date
            FROM helios.silver.shipping_clean
            WHERE tenant_id = tenant_id_param 
              AND batch_id = batch_id_param 
              AND is_valid = true 
              AND actual_date IS NOT NULL
        ),
        distinct_dates AS (
            SELECT DISTINCT full_date
            FROM extracted_dates
            WHERE full_date IS NOT NULL
        )
        SELECT
            cast(date_format(full_date, 'yyyyMMdd') AS bigint) AS date_id,
            full_date,
            day(full_date) AS day,
            month(full_date) AS month,
            quarter(full_date) AS quarter,
            year(full_date) AS year,
            dayofweek(full_date) AS day_of_week,
            CASE WHEN dayofweek(full_date) IN (1, 7) THEN true ELSE false END AS is_weekend
        FROM distinct_dates
    ) AS source
    ON target.date_id = source.date_id
    WHEN NOT MATCHED THEN
        INSERT (date_id, full_date, day, month, quarter, year, day_of_week, is_weekend)
        VALUES (source.date_id, source.full_date, source.day, source.month, source.quarter, source.year, source.day_of_week, source.is_weekend);
END;
