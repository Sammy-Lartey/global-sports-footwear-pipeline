-- Drop tables if they exist
DROP TABLE IF EXISTS sports_footwear_sales_clean;
DROP TABLE IF EXISTS sports_footwear_sales_raw;

-- Create raw table (Bronze layer)
CREATE TABLE sports_footwear_sales_raw (
    order_id VARCHAR(255),
    order_date DATE,
    brand VARCHAR(255),
    model_name VARCHAR(255),
    category VARCHAR(255),
    gender VARCHAR(50),
    size DECIMAL(5, 2),
    color VARCHAR(50),
    base_price_usd DECIMAL(15, 4),
    discount_percent DECIMAL(5, 2),
    final_price_usd DECIMAL(15, 4),
    units_sold INT,
    revenue_usd DECIMAL(15, 4),
    payment_method VARCHAR(50),
    sales_channel VARCHAR(50),
    country VARCHAR(100),
    customer_income_level VARCHAR(50),
    customer_rating DECIMAL(3, 2),
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create clean table (Silver layer)
CREATE TABLE sports_footwear_sales_clean (
    orderId VARCHAR(255) PRIMARY KEY,
    orderDate DATE,
    brand VARCHAR(255),
    modelName VARCHAR(255),
    category VARCHAR(255),
    gender VARCHAR(50),
    size DECIMAL(5, 2),
    color VARCHAR(50),
    basePriceUsd DECIMAL(15, 4),
    discountPercent DECIMAL(5, 2),
    finalPriceUsd DECIMAL(15, 4),
    unitsSold INT,
    revenueUsd DECIMAL(15, 4),
    paymentMethod VARCHAR(50),
    salesChannel VARCHAR(50),
    country VARCHAR(100),
    customerIncomeLevel VARCHAR(50),
    customerRating DECIMAL(3, 2),
    year INT,
    month INT,
    dayOfWeek INT,
    discountAmount DECIMAL(15, 4),
    validationTimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add some indexes for better performance
CREATE INDEX idx_brand ON sports_footwear_sales_clean(brand);
CREATE INDEX idx_orderdate ON sports_footwear_sales_clean(orderDate);