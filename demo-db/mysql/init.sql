-- =====================================================================
-- Helios Demo Database: MySQL Initialization Script
-- Service: demo-mysql (Host port: 3307, Container port: 3306)
-- Used for Live Database Connection Ingestion Demos (Tenant 7)
--
-- NOTE: Microsoft SQL Server is supported in application code
-- but is not containerized due to Docker image size (>1.5 GB).
-- =====================================================================

CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(50),
    order_date VARCHAR(50),
    customer_name VARCHAR(255),
    product_name VARCHAR(255),
    category VARCHAR(100),
    quantity VARCHAR(50),
    unit_price VARCHAR(50),
    discount VARCHAR(50),
    total VARCHAR(50),
    shipping_mode VARCHAR(100),
    delivery_status VARCHAR(100),
    scheduled_days INT,
    actual_days INT,
    INDEX idx_orders_order_id (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
