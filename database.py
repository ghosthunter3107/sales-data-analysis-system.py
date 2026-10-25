"""
Database Management Module for Sales Data Analysis System
Uses SQLite3 for zero-configuration, reliable local execution,
fully conforming to the relational entities (products, sales)
specified in the MySQL schema.
"""

import sqlite3
import os

DEFAULT_DB_FILE = os.path.join(os.path.dirname(__file__), "sales_system.db")

def get_db_connection(db_file=None):
    """Returns an active SQLite database connection with row factory enabled."""
    target_db = db_file if db_file else DEFAULT_DB_FILE
    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_file=None):
    """
    Initializes the relational tables:
    - products(product_id, product_name, category)
    - sales(sale_id, product_id, sale_date, quantity, unit_price, region, total_amount)
    """
    conn = get_db_connection(db_file)
    cursor = conn.cursor()

    # 1. Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Sales table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            sale_date TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price REAL NOT NULL CHECK (unit_price >= 0),
            region TEXT NOT NULL,
            total_amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
        )
    """)

    # Default catalog seeds
    sample_products = [
        ('P101', 'Enterprise Server Pro', 'Hardware'),
        ('P102', 'Cloud Storage Annual', 'Cloud Services'),
        ('P103', 'AI Analytics Suite', 'Software'),
        ('P104', 'Cybersecurity Gateway', 'Security'),
        ('P105', 'Developer Workstation', 'Hardware'),
        ('P106', 'Database License Core', 'Software')
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO products (product_id, product_name, category)
        VALUES (?, ?, ?)
    """, sample_products)

    conn.commit()
    conn.close()

def save_sales_records(records, duplicate_policy="SKIP", db_file=None):
    """
    Saves validated sales records into the database applying the documented duplicate policy.
    Handles duplicate IDs in the batch as well as duplicates already in the database.

    Policies:
      - 'SKIP': Keeps existing record, ignores new incoming record.
      - 'OVERWRITE': Replaces existing record with the incoming record.
      - 'APPEND': Generates a unique suffixed ID (e.g. S1001_dup1) and inserts record.

    Returns:
      dict: { 'inserted': int, 'updated': int, 'skipped': int, 'duplicates': int }
    """
    conn = get_db_connection(db_file)
    cursor = conn.cursor()

    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    duplicate_count = 0

    for rec in records:
        sale_id = str(rec['sale_id']).strip()
        product_id = str(rec['product_id']).strip()
        product_name = str(rec.get('product_name') or f"Product {product_id}").strip()
        category = str(rec.get('category') or 'General').strip()
        sale_date = str(rec['sale_date']).strip()
        quantity = int(rec['quantity'])
        unit_price = float(rec['unit_price'])
        region = str(rec['region']).strip()
        total_amount = round(quantity * unit_price, 2)

        # Ensure product catalog consistency
        cursor.execute("SELECT product_id FROM products WHERE product_id = ?", (product_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO products (product_id, product_name, category)
                VALUES (?, ?, ?)
            """, (product_id, product_name, category))

        # Check if sale_id already exists in the database
        cursor.execute("SELECT sale_id FROM sales WHERE sale_id = ?", (sale_id,))
        exists = cursor.fetchone()

        if exists:
            duplicate_count += 1
            policy_upper = str(duplicate_policy).upper()
            if policy_upper == "SKIP":
                skipped_count += 1
                continue
            elif policy_upper == "OVERWRITE":
                cursor.execute("""
                    UPDATE sales
                    SET product_id = ?, sale_date = ?, quantity = ?, unit_price = ?, region = ?, total_amount = ?
                    WHERE sale_id = ?
                """, (product_id, sale_date, quantity, unit_price, region, total_amount, sale_id))
                updated_count += 1
            elif policy_upper == "APPEND":
                suffix = 1
                new_id = f"{sale_id}_dup{suffix}"
                while True:
                    cursor.execute("SELECT sale_id FROM sales WHERE sale_id = ?", (new_id,))
                    if not cursor.fetchone():
                        break
                    suffix += 1
                    new_id = f"{sale_id}_dup{suffix}"
                cursor.execute("""
                    INSERT INTO sales (sale_id, product_id, sale_date, quantity, unit_price, region, total_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (new_id, product_id, sale_date, quantity, unit_price, region, total_amount))
                inserted_count += 1
            else:
                # Default fallback is SKIP
                skipped_count += 1
                continue
        else:
            cursor.execute("""
                INSERT INTO sales (sale_id, product_id, sale_date, quantity, unit_price, region, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sale_id, product_id, sale_date, quantity, unit_price, region, total_amount))
            inserted_count += 1

    conn.commit()
    conn.close()

    return {
        "inserted": inserted_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "duplicates": duplicate_count
    }

def get_all_records(db_file=None):
    """Retrieves all sales records ordered chronologically by sale_date."""
    conn = get_db_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.sale_id, s.product_id, p.product_name, p.category,
               s.sale_date, s.quantity, s.unit_price, s.region, s.total_amount
        FROM sales s
        LEFT JOIN products p ON s.product_id = p.product_id
        ORDER BY s.sale_date DESC, s.sale_id ASC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def clear_all_sales(db_file=None):
    """Safely clears sales records without dropping table definitions."""
    conn = get_db_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sales")
    conn.commit()
    conn.close()
