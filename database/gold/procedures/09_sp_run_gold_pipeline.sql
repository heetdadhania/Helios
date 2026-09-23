-- =====================================================================
-- Helios Gold Layer Master Procedure: Run Complete Gold Pipeline
-- =====================================================================

USE CATALOG helios;
USE SCHEMA gold;

CREATE OR REPLACE PROCEDURE helios.gold.sp_run_gold_pipeline (
    IN tenant_id_param BIGINT,
    IN batch_id_param STRING
)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Master Gold pipeline orchestration procedure executing dimension loads, fact loads, and roll-ups with audit tracking'
AS BEGIN
    DECLARE start_time TIMESTAMP DEFAULT current_timestamp();
    DECLARE total_loaded BIGINT DEFAULT 0;
    DECLARE error_msg STRING DEFAULT 'Unknown SQL exception occurred during gold pipeline execution';

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        -- Update pipeline_status to failed state (stage='gold')
        UPDATE helios.platform.pipeline_status
        SET stage = 'gold',
            status = 'failed',
            error_message = error_msg,
            updated_at = current_timestamp()
        WHERE batch_id = batch_id_param;

        -- Record failure into meta.etl_audit_log
        INSERT INTO helios.meta.etl_audit_log (
            batch_id, stage, row_count, status, started_at, completed_at, error_message
        )
        VALUES (
            batch_id_param,
            'gold_transform',
            0,
            'failed',
            start_time,
            current_timestamp(),
            error_msg
        );
    END;

    -- Step 1: Load Conformed Date Dimension
    CALL helios.gold.sp_load_dim_date(tenant_id_param, batch_id_param);

    -- Step 2: Load Tenant Product Dimension
    CALL helios.gold.sp_load_dim_product(tenant_id_param, batch_id_param);

    -- Step 3: Load Tenant Customer Dimension
    CALL helios.gold.sp_load_dim_customer(tenant_id_param, batch_id_param);

    -- Step 4: Load Conformed Shipping Mode Dimension
    CALL helios.gold.sp_load_dim_shipping_mode(tenant_id_param, batch_id_param);

    -- Step 5: Load Conformed Delivery Status Dimension
    CALL helios.gold.sp_load_dim_delivery_status(tenant_id_param, batch_id_param);

    -- Step 6: Load Transactional Orders Fact Table
    CALL helios.gold.sp_load_fact_orders(tenant_id_param, batch_id_param);

    -- Step 7: Load Fulfillment Shipments Fact Table
    CALL helios.gold.sp_load_fact_shipments(tenant_id_param, batch_id_param);

    -- Step 8: Refresh Pre-Aggregated Daily Orders & Revenue Summary
    CALL helios.gold.sp_refresh_daily_summary(tenant_id_param, batch_id_param);

    -- Calculate total rows loaded for this batch
    SET total_loaded = (
        SELECT count(*) FROM helios.gold.fact_orders WHERE batch_id = batch_id_param
    ) + (
        SELECT count(*) FROM helios.gold.fact_shipments WHERE batch_id = batch_id_param
    );

    -- Step 9: Update pipeline_status to 'success'
    UPDATE helios.platform.pipeline_status
    SET stage = 'gold_transform',
        status = 'success',
        error_message = NULL,
        updated_at = current_timestamp()
    WHERE batch_id = batch_id_param;

    -- Step 10: Record successful execution in meta.etl_audit_log
    INSERT INTO helios.meta.etl_audit_log (
        batch_id, stage, row_count, status, started_at, completed_at, error_message
    )
    VALUES (
        batch_id_param,
        'gold_transform',
        total_loaded,
        'completed',
        start_time,
        current_timestamp(),
        NULL
    );
END;
