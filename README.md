# Project 4: Sales Data Analysis System

> **Difficulty Level**: Beginner (BTech Project)  
> **Primary Technologies**: Python 3.14, Pandas, NumPy, Matplotlib, SQLite3, Flask, HTML5, CSS3, JavaScript (Chart.js, PapaParse)  
> **Database Architecture**: SQLite3 (Active Embedded Database) with complete MySQL 8.0 DDL compatibility (`schema.sql`)

---

## 1. Project Overview & Objectives

The **Sales Data Analysis System** is an end-to-end data processing and business intelligence platform designed for ingesting sales transactions, validating input integrity, maintaining relational data, and analyzing business performance.

### Key Objectives:
1. **CSV Ingestion & Multi-Stage Validation:** Ingest external sales data, enforce strict schema rules, and report row-by-row validation errors.
2. **Relational Data Persistence:** Store valid transactions and maintain entity relationships between `products` and `sales`.
3. **Documented Duplicate Import Policies:** Provide `SKIP`, `OVERWRITE`, and `APPEND` policies to handle primary key collisions gracefully.
4. **Analytical Calculations (Pandas & NumPy):** Compute revenue, volume, average order value, product rankings, and month-over-month (MoM) growth rates.
5. **Executive Visualization (Chart.js & Matplotlib):** Display interactive web dashboards and generate high-resolution publication charts.

---

## 2. System Architecture & Tech Stack

```
                          ┌─────────────────────────────────────┐
                          │         Web Browser Dashboard       │
                          │   (index.html, style.css, app.js)   │
                          └──────────────────┬──────────────────┘
                                             │ HTTP / REST API
                          ┌──────────────────▼──────────────────┐
                          │         Flask Web Server            │
                          │             (app.py)                │
                          └───────┬─────────────────────┬───────┘
                                  │                     │
                    ┌─────────────▼─────┐         ┌─────▼─────────────┐
                    │ Data Analysis     │         │ Database Engine   │
                    │ (analysis.py)     │         │ (database.py)     │
                    │ - Pandas          │         │ - SQLite3         │
                    │ - NumPy           │         │ - Foreign Keys    │
                    │ - Matplotlib      │         │ - sales_system.db │
                    └───────────────────┘         └───────────────────┘
```

---

## 3. Database Specification & Schema

The project utilizes **SQLite3** as its active embedded relational database engine for zero-configuration, reliable execution, while maintaining 100% relational parity with the specified **MySQL 8.0** schema in [`schema.sql`](file:///c:/Users/nanil/Downloads/sales/schema.sql).

### Relational Entities:
1. **`products` Table** (Catalog):
   - `product_id VARCHAR(50) PRIMARY KEY`: Unique product identifier (e.g., `P101`).
   - `product_name VARCHAR(255) NOT NULL`: Human-readable product label.
   - `category VARCHAR(100) NOT NULL`: Product grouping (Hardware, Software, Cloud Services, Security).
   - `created_at TIMESTAMP`: Record creation timestamp.

2. **`sales` Table** (Transactions):
   - `sale_id VARCHAR(50) PRIMARY KEY`: Unique transaction identifier (e.g., `S1001`).
   - `product_id VARCHAR(50) NOT NULL REFERENCES products(product_id)`: Foreign key relationship.
   - `sale_date DATE NOT NULL`: Transaction date (`YYYY-MM-DD`).
   - `quantity INT NOT NULL CHECK (quantity > 0)`: Units sold (positive integer).
   - `unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0)`: Unit selling price (non-negative).
   - `region VARCHAR(100) NOT NULL`: Geographic operating territory.
   - `total_amount DECIMAL(12,2)`: Calculated revenue (`quantity * unit_price`).

---

## 4. CSV Schema & Validation Rules

Uploaded files must contain the following header columns (case-insensitive):
```csv
sale_id,product_id,product_name,category,sale_date,quantity,unit_price,region
```

### Validation Matrix:
| Field | Data Type | Constraint / Rule | Rejection Reason |
| :--- | :--- | :--- | :--- |
| `sale_id` | Text / String | Mandatory, non-empty, unique | Missing ID or in-file duplicate |
| `product_id` | Text / String | Mandatory, non-empty | Missing product ID |
| `sale_date` | Date | Valid ISO or standard date format | Invalid calendar date (e.g., `2026-02-30`) |
| `quantity` | Integer | Positive integer strictly `> 0` | Non-integer, zero, or negative (`<= 0`) |
| `unit_price`| Float / Numeric | Non-negative numeric strictly `≥ 0` | Non-numeric or negative (`< 0`) |
| `region` | Text / String | Mandatory, non-empty | Missing or blank region |

---

## 5. Documented Duplicate Import Policies

When an imported record contains a `sale_id` that already exists (either within the database or earlier in the same CSV), the system applies the chosen policy:

1. **`SKIP` (Default Standard):**
   - Retains the existing record untouched.
   - Discards the incoming duplicate record.
   - Increments the `skipped` counter and logs the collision in the audit report.
   - **Use Case:** Prevents accidental modification of established historical records.

2. **`OVERWRITE` (Data Refresh):**
   - Updates the existing database record with the new incoming attributes (`quantity`, `unit_price`, `sale_date`, `region`, `total_amount`).
   - Increments the `updated` counter.
   - **Use Case:** Applying batch adjustments, corrections, or price updates.

3. **`APPEND` (Historical Preservation):**
   - Retains both records by automatically generating a unique suffixed identifier (e.g., `S1001_dup1`, `S1001_dup2`).
   - Inserts the record as a distinct entry.
   - Increments the `inserted` counter.
   - **Use Case:** Preserving duplicate transaction events without database collision.

---

## 6. Analytical Metrics & Formulae

All metrics are calculated using **Pandas** and **NumPy**:

- **Total Revenue:** Vectorized calculation across all sales:
  $$\text{Total Revenue} = \sum_{i=1}^{N} (\text{Quantity}_i \times \text{Unit Price}_i)$$
- **Total Units Sold:** Sum of units: $\sum \text{Quantity}_i$
- **Average Order Value (AOV):** $\frac{\text{Total Revenue}}{N}$
- **Product Rankings:** Aggregation by `product_id` with revenue contribution percentage:
  $$\text{Revenue Share} = \left(\frac{\text{Product Revenue}}{\text{Total Revenue}}\right) \times 100$$
- **Month-over-Month (MoM) Growth Rate:** Percentage change between sequential months:
  $$\text{MoM Growth Rate} = \left(\frac{\text{Revenue}_t - \text{Revenue}_{t-1}}{\text{Revenue}_{t-1}}\right) \times 100$$

---

## 7. Setup & Execution Instructions

### Prerequisites
- Python 3.10+ (tested with Python 3.14)
- Packages: `Flask`, `pandas`, `numpy`, `matplotlib`

### Installation
```bash
pip install flask pandas numpy matplotlib
```

### Running the Web Server
```bash
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

### Direct Browser Execution (Fallback)
If Python is not running, double-click **`index.html`** or **`run_system.bat`** to run the zero-dependency client analytic engine with pre-loaded clean sample data.

---

## 8. Verification & Automated Test Suite

A comprehensive 14-point test suite is provided in [`test_sales_analysis.py`](file:///c:/Users/nanil/Downloads/sales/test_sales_analysis.py):

```bash
python test_sales_analysis.py
```

### Test Coverage Matrix:
1. `test_01_valid_csv_upload`: Validates correct CSV ingestion.
2. `test_02_missing_required_columns`: Verifies rejection when mandatory headers are missing.
3. `test_03_invalid_dates`: Detects invalid dates (e.g., `2026-02-30`, `NOT-A-DATE`).
4. `test_04_missing_sale_ids`: Flags missing or blank sale IDs.
5. `test_05_invalid_quantities`: Rejects zero, negative, and decimal quantities.
6. `test_06_invalid_and_negative_prices`: Rejects non-numeric and negative unit prices.
7. `test_07_missing_required_values`: Detects missing `product_id` and `region`.
8. `test_08_duplicate_ids_within_one_csv`: Detects and reports duplicate IDs inside the CSV.
9. `test_09_duplicate_ids_already_in_database`: Flags incoming records matching existing DB keys.
10. `test_10_duplicate_policies`: Tests `SKIP`, `OVERWRITE`, and `APPEND` behaviors.
11. `test_11_revenue_calculations`: Tests `Quantity * Price`, total revenue, and average order value.
12. `test_12_monthly_aggregation_and_product_rankings`: Verifies Pandas grouping and MoM growth rate.
13. `test_13_mixed_valid_and_invalid_rows`: Confirms partial import of valid rows while reporting invalid rows.
14. `test_14_empty_csv_and_headers_only`: Handles completely empty files and header-only files.
