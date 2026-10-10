-- =====================================================================
-- Helios Demo Database: PostgreSQL Initialization Script
-- Service: demo-postgres (Host port: 5433, Container port: 5432)
-- Used for Live Database Connection Ingestion Demos (Tenant 6)
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
    actual_days INT
);

CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id);
