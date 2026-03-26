-- Create schema
DROP SCHEMA IF EXISTS analytics CASCADE;
CREATE SCHEMA analytics;

-- 1. Brand performance
CREATE TABLE analytics.gold_brand_performance (
    brand VARCHAR(255) PRIMARY KEY,
    total_revenue_usd DECIMAL(20, 4),
    total_units_sold BIGINT,
    total_orders BIGINT,
    avg_customer_rating DECIMAL(3, 2)
);

-- 2. Monthly sales
CREATE TABLE analytics.gold_monthly_sales (
    year INT,
    month VARCHAR(20),
    total_revenue_usd DECIMAL(20, 4),
    total_units_sold BIGINT,
    total_orders BIGINT,
    PRIMARY KEY (year, month)
);

-- 3. Channel performance
CREATE TABLE analytics.gold_channel_performance (
    "salesChannel" VARCHAR(50) PRIMARY KEY,
    total_revenue_usd DECIMAL(20, 4),
    total_orders BIGINT,
    avg_units_per_order DECIMAL(10, 4)
);

-- 4. Country performance
CREATE TABLE analytics.gold_country_performance (
    country VARCHAR(100) PRIMARY KEY,
    total_revenue_usd DECIMAL(20, 4),
    total_orders BIGINT
);

-- 5. Overall metrics (single row)
CREATE TABLE analytics.gold_overall_metrics (
    id INT PRIMARY KEY DEFAULT 1,
    total_revenue_usd DECIMAL(20, 4),
    total_units_sold BIGINT,
    total_orders BIGINT,
    avg_customer_rating DECIMAL(3, 2)
);