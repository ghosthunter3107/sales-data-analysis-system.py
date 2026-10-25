-- ===================================================
-- Project 4: Sales Data Analysis System
-- MySQL Database Schema
-- Entities: products, sales
-- ===================================================

CREATE DATABASE IF NOT EXISTS sales_db;
USE sales_db;

-- 1. Products Table
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Sales Table
CREATE TABLE IF NOT EXISTS sales (
    sale_id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    sale_date DATE NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    region VARCHAR(100) NOT NULL,
    total_amount DECIMAL(12, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- Indexes for optimized analytical queries
CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_sales_product ON sales(product_id);
CREATE INDEX idx_sales_region ON sales(region);

-- Initial Sample Products Seed
INSERT INTO products (product_id, product_name, category) VALUES
('P101', 'Enterprise Server Pro', 'Hardware'),
('P102', 'Cloud Storage Annual', 'Cloud Services'),
('P103', 'AI Analytics Suite', 'Software'),
('P104', 'Cybersecurity Gateway', 'Security'),
('P105', 'Developer Workstation', 'Hardware'),
('P106', 'Database License Core', 'Software')
ON DUPLICATE KEY UPDATE product_name = VALUES(product_name);
