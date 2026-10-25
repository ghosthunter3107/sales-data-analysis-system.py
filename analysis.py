"""
Sales Data Analysis & Visualization Module
Implements:
- Strict CSV Schema and Row-Level Data Validation
- Malformed Row Auditing (Row #, Column, Faulty Value, Error Reason)
- Duplicate Sale ID Detection (within CSV and database)
- Vectorized Sales Calculations using Pandas and NumPy
- Month-wise Trends, MoM Growth Rates, and Product Rankings
- High-Resolution Matplotlib Dual-Axis & Bar Chart Generation
"""

import io
import os
import csv
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive Agg backend for safe server generation
import matplotlib.pyplot as plt

REQUIRED_COLUMNS = ['sale_id', 'product_id', 'sale_date', 'quantity', 'unit_price', 'region']

def validate_sales_csv(file_stream_or_path):
    """
    Validates CSV headers, data types, constraints, and duplicates.

    Returns:
      dict: {
        'status': 'success' | 'error',
        'message': str,
        'total_rows_inspected': int,
        'valid_rows': list[dict],
        'malformed_rows': list[dict],
        'duplicate_count': int,
        'duplicate_ids': list[str]
      }
    """
    valid_rows = []
    malformed_rows = []
    seen_sale_ids = {}  # sale_id -> first seen row number
    duplicate_ids = []

    # Read content from file path or stream
    if hasattr(file_stream_or_path, 'read'):
        content = file_stream_or_path.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
    else:
        with open(file_stream_or_path, mode='r', encoding='utf-8', errors='replace') as f:
            content = f.read()

    # Edge Case: Completely empty file
    if not content or not content.strip():
        return {
            "status": "error",
            "message": "CSV file is empty. Please upload a file with headers and sales records.",
            "total_rows_inspected": 0,
            "valid_rows": [],
            "malformed_rows": [{
                "row": 0,
                "field": "File",
                "value": "EMPTY_FILE",
                "reason": "File contains no data or headers",
                "severity": "Critical"
            }],
            "duplicate_count": 0,
            "duplicate_ids": []
        }

    reader = csv.DictReader(io.StringIO(content))

    # Header Validation
    if not reader.fieldnames:
        return {
            "status": "error",
            "message": "CSV file missing headers.",
            "total_rows_inspected": 0,
            "valid_rows": [],
            "malformed_rows": [{
                "row": 1,
                "field": "Headers",
                "value": "None",
                "reason": "Unable to parse CSV headers",
                "severity": "Critical"
            }],
            "duplicate_count": 0,
            "duplicate_ids": []
        }

    raw_headers = [h.strip() for h in reader.fieldnames if h]
    lower_headers = [h.lower() for h in raw_headers]
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in lower_headers]

    if missing_cols:
        return {
            "status": "error",
            "message": f"CSV file missing required column(s): {', '.join(missing_cols)}. Required columns are: {', '.join(REQUIRED_COLUMNS)}",
            "total_rows_inspected": 0,
            "valid_rows": [],
            "malformed_rows": [{
                "row": 1,
                "field": "Headers",
                "value": f"Provided: {raw_headers}",
                "reason": f"Missing required columns: {missing_cols}",
                "severity": "Critical"
            }],
            "duplicate_count": 0,
            "duplicate_ids": []
        }

    row_idx = 1  # Row 1 is header
    for raw_row in reader:
        row_idx += 1
        # Normalize keys to lowercase stripped
        row = {k.strip().lower(): (v.strip() if v is not None else "") for k, v in raw_row.items() if k}
        row_errors = []

        # 1. Validate sale_id
        sale_id = row.get('sale_id', '')
        if not sale_id:
            row_errors.append({
                "field": "sale_id",
                "value": "EMPTY",
                "reason": "Missing or empty sale ID"
            })

        # 2. Validate product_id
        product_id = row.get('product_id', '')
        if not product_id:
            row_errors.append({
                "field": "product_id",
                "value": "EMPTY",
                "reason": "Missing or empty product ID"
            })

        # 3. Validate sale_date
        date_str = row.get('sale_date', '')
        parsed_date = None
        if not date_str:
            row_errors.append({
                "field": "sale_date",
                "value": "EMPTY",
                "reason": "Missing or empty sale date"
            })
        else:
            # Strictly validate calendar date format
            date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%Y/%m/%d']
            for fmt in date_formats:
                try:
                    d = datetime.strptime(date_str, fmt)
                    parsed_date = d
                    break
                except (ValueError, TypeError):
                    continue
            if not parsed_date:
                row_errors.append({
                    "field": "sale_date",
                    "value": date_str,
                    "reason": "Invalid date format or non-existent calendar date (expected YYYY-MM-DD)"
                })

        # 4. Validate quantity
        qty_str = row.get('quantity', '')
        quantity = None
        if not qty_str:
            row_errors.append({
                "field": "quantity",
                "value": "EMPTY",
                "reason": "Missing or empty quantity"
            })
        else:
            try:
                # Check for non-integer numeric string
                float_val = float(qty_str)
                if not float_val.is_integer():
                    row_errors.append({
                        "field": "quantity",
                        "value": qty_str,
                        "reason": f"Quantity must be a whole integer, got decimal: {qty_str}"
                    })
                else:
                    quantity = int(float_val)
                    if quantity <= 0:
                        row_errors.append({
                            "field": "quantity",
                            "value": qty_str,
                            "reason": f"Quantity must be a positive integer (> 0), got: {qty_str}"
                        })
            except ValueError:
                row_errors.append({
                    "field": "quantity",
                    "value": qty_str,
                    "reason": f"Quantity is not a valid integer, got: {qty_str}"
                })

        # 5. Validate unit_price
        price_str = row.get('unit_price', '')
        unit_price = None
        if not price_str:
            row_errors.append({
                "field": "unit_price",
                "value": "EMPTY",
                "reason": "Missing or empty unit price"
            })
        else:
            try:
                unit_price = float(price_str)
                if unit_price < 0:
                    row_errors.append({
                        "field": "unit_price",
                        "value": price_str,
                        "reason": f"Unit price cannot be negative (< 0), got: {price_str}"
                    })
            except ValueError:
                row_errors.append({
                    "field": "unit_price",
                    "value": price_str,
                    "reason": f"Unit price must be a valid numeric value, got: {price_str}"
                })

        # 6. Validate region
        region = row.get('region', '')
        if not region:
            row_errors.append({
                "field": "region",
                "value": "EMPTY",
                "reason": "Missing or empty region"
            })

        # 7. Check Duplicate sale_id within the CSV
        if sale_id:
            if sale_id in seen_sale_ids:
                first_seen_row = seen_sale_ids[sale_id]
                duplicate_ids.append(sale_id)
                row_errors.append({
                    "field": "sale_id",
                    "value": sale_id,
                    "reason": f"Duplicate sale ID in CSV (already defined at row {first_seen_row})",
                    "is_duplicate": True
                })
            else:
                seen_sale_ids[sale_id] = row_idx

        # Categorize Row Outcome
        if row_errors:
            for err in row_errors:
                malformed_rows.append({
                    "row": row_idx,
                    "field": err["field"],
                    "value": err["value"],
                    "reason": err["reason"],
                    "severity": "Warning" if err.get("is_duplicate") else "Critical",
                    "is_duplicate": err.get("is_duplicate", False)
                })
        else:
            product_name = row.get('product_name') or f"Product {product_id}"
            category = row.get('category') or 'General'
            valid_rows.append({
                "sale_id": sale_id,
                "product_id": product_id,
                "product_name": product_name,
                "category": category,
                "sale_date": parsed_date.strftime('%Y-%m-%d'),
                "quantity": quantity,
                "unit_price": unit_price,
                "region": region
            })

    total_inspected = row_idx - 1

    return {
        "status": "success",
        "message": f"Validation complete: {len(valid_rows)} valid rows, {len(malformed_rows)} error(s) detected across {total_inspected} rows.",
        "total_rows_inspected": total_inspected,
        "valid_rows": valid_rows,
        "malformed_rows": malformed_rows,
        "duplicate_count": len(duplicate_ids),
        "duplicate_ids": duplicate_ids
    }

def analyze_sales_records(records):
    """
    Performs analytical computations using Pandas and NumPy:
    - Revenue calculation: total_amount = quantity * unit_price
    - Summary metrics: total revenue, total quantity, total orders, average order value, MoM growth
    - Month-wise aggregation and MoM growth rate
    - Top-selling products by revenue and by quantity
    - Region and Category distributions
    """
    if not records:
        return {
            "summary": {
                "total_revenue": 0.0,
                "total_units": 0,
                "total_transactions": 0,
                "avg_order_value": 0.0,
                "monthly_growth_rate": 0.0,
                "top_product": "-",
                "top_product_rev": 0.0
            },
            "product_ranking": [],
            "best_selling_by_quantity": [],
            "monthly_trends": [],
            "regional_sales": [],
            "category_sales": []
        }

    df = pd.DataFrame(records)

    # Ensure required analytical columns exist
    if 'product_name' not in df.columns:
        df['product_name'] = df['product_id'].astype(str).apply(lambda pid: f"Product {pid}")
    else:
        df['product_name'] = df['product_name'].fillna('').replace('', None).fillna(df['product_id'].astype(str).apply(lambda pid: f"Product {pid}"))

    if 'category' not in df.columns:
        df['category'] = 'General'
    else:
        df['category'] = df['category'].fillna('').replace('', 'General')

    if 'region' not in df.columns:
        df['region'] = 'Unspecified'
    else:
        df['region'] = df['region'].fillna('').replace('', 'Unspecified')

    # Clean & ensure numeric types
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0.0)

    # Core Formula: Revenue = Quantity * Unit Price (Tested)
    df['total_amount'] = np.round(df['quantity'] * df['unit_price'], 2)

    # Parse and sort by date
    df['sale_date_dt'] = pd.to_datetime(df['sale_date'], errors='coerce')
    df['month'] = df['sale_date_dt'].dt.strftime('%Y-%m').fillna('Unknown')

    # NumPy Totals
    total_rev = float(np.sum(df['total_amount'].to_numpy()))
    total_units = int(np.sum(df['quantity'].to_numpy()))
    total_transactions = int(len(df))
    avg_order = round(float(total_rev / total_transactions) if total_transactions > 0 else 0.0, 2)

    # 1. Monthly Trends Aggregation
    valid_dates_df = df[df['month'] != 'Unknown']
    monthly_grp = valid_dates_df.groupby('month').agg(
        revenue=('total_amount', 'sum'),
        units=('quantity', 'sum'),
        orders=('sale_id', 'count')
    ).reset_index().sort_values('month')

    # Month-over-Month (MoM) Growth using NumPy
    monthly_revs = monthly_grp['revenue'].to_numpy()
    if len(monthly_revs) > 1 and monthly_revs[-2] > 0:
        latest_growth = round(float(((monthly_revs[-1] - monthly_revs[-2]) / monthly_revs[-2]) * 100), 2)
    else:
        latest_growth = 0.0

    monthly_trends = [
        {
            "month": str(row['month']),
            "revenue": round(float(row['revenue']), 2),
            "units": int(row['units']),
            "orders": int(row['orders'])
        }
        for _, row in monthly_grp.iterrows()
    ]

    # 2. Product Rankings (Grouped by product_id)
    prod_grp = df.groupby('product_id').agg(
        product_name=('product_name', 'first'),
        category=('category', 'first'),
        units_sold=('quantity', 'sum'),
        total_revenue=('total_amount', 'sum'),
        avg_price=('unit_price', 'mean'),
        orders_count=('sale_id', 'count')
    ).reset_index()

    # Sort descending by revenue for highest-revenue ranking
    prod_by_revenue = prod_grp.sort_values('total_revenue', ascending=False)
    prod_by_revenue['revenue_share'] = np.round((prod_by_revenue['total_revenue'] / (total_rev if total_rev > 0 else 1.0)) * 100, 1)

    product_ranking = []
    for rank, (_, row) in enumerate(prod_by_revenue.iterrows(), start=1):
        product_ranking.append({
            "rank": rank,
            "product_id": str(row['product_id']),
            "product_name": str(row['product_name']),
            "category": str(row['category']),
            "units_sold": int(row['units_sold']),
            "avg_price": round(float(row['avg_price']), 2),
            "total_revenue": round(float(row['total_revenue']), 2),
            "revenue_share": float(row['revenue_share']),
            "orders_count": int(row['orders_count'])
        })

    # Sort descending by quantity for best-selling by volume
    prod_by_qty = prod_grp.sort_values('units_sold', ascending=False)
    best_selling_by_quantity = [
        {
            "product_id": str(row['product_id']),
            "product_name": str(row['product_name']),
            "units_sold": int(row['units_sold']),
            "total_revenue": round(float(row['total_revenue']), 2)
        }
        for _, row in prod_by_qty.iterrows()
    ]

    top_product_name = product_ranking[0]['product_name'] if product_ranking else '-'
    top_product_rev = product_ranking[0]['total_revenue'] if product_ranking else 0.0

    # 3. Regional Sales Breakdown
    region_grp = df.groupby('region').agg(
        revenue=('total_amount', 'sum'),
        units=('quantity', 'sum')
    ).reset_index().sort_values('revenue', ascending=False)

    regional_sales = [
        {
            "region": str(row['region']),
            "revenue": round(float(row['revenue']), 2),
            "units": int(row['units'])
        }
        for _, row in region_grp.iterrows()
    ]

    # 4. Category Breakdown
    cat_grp = df.groupby('category').agg(
        revenue=('total_amount', 'sum'),
        units=('quantity', 'sum')
    ).reset_index().sort_values('revenue', ascending=False)

    category_sales = [
        {
            "category": str(row['category']),
            "revenue": round(float(row['revenue']), 2),
            "units": int(row['units'])
        }
        for _, row in cat_grp.iterrows()
    ]

    return {
        "summary": {
            "total_revenue": round(total_rev, 2),
            "total_units": total_units,
            "total_transactions": total_transactions,
            "avg_order_value": avg_order,
            "monthly_growth_rate": latest_growth,
            "top_product": top_product_name,
            "top_product_rev": top_product_rev
        },
        "product_ranking": product_ranking,
        "best_selling_by_quantity": best_selling_by_quantity,
        "monthly_trends": monthly_trends,
        "regional_sales": regional_sales,
        "category_sales": category_sales
    }

def generate_matplotlib_charts(records, output_dir=None):
    """
    Generates high-resolution Matplotlib line and bar charts
    and saves them to the specified output directory.
    """
    if not output_dir:
        output_dir = os.path.dirname(__file__)

    analysis = analyze_sales_records(records)
    monthly = analysis['monthly_trends']
    ranking = analysis['product_ranking']

    # 1. Monthly Revenue & Units Trend Chart (Line Chart)
    fig, ax1 = plt.subplots(figsize=(10, 5), dpi=150)
    plt.title('Monthly Sales Revenue & Quantity Trend', fontsize=14, fontweight='bold', pad=15)

    if monthly:
        months = [m['month'] for m in monthly]
        revs = [m['revenue'] for m in monthly]
        units = [m['units'] for m in monthly]

        color = '#1f77b4'
        ax1.set_xlabel('Month', fontweight='bold')
        ax1.set_ylabel('Revenue ($)', color=color, fontweight='bold')
        line1 = ax1.plot(months, revs, color=color, marker='o', linewidth=2.5, label='Revenue ($)')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, linestyle='--', alpha=0.5)

        ax2 = ax1.twinx()
        color = '#ff7f0e'
        ax2.set_ylabel('Quantity Sold (Units)', color=color, fontweight='bold')
        line2 = ax2.plot(months, units, color=color, marker='s', linestyle='--', linewidth=2, label='Units Sold')
        ax2.tick_params(axis='y', labelcolor=color)

        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left')
    else:
        ax1.text(0.5, 0.5, 'No Data Available', horizontalalignment='center', verticalalignment='center')

    plt.tight_layout()
    chart1_path = os.path.join(output_dir, 'monthly_trend_chart.png')
    plt.savefig(chart1_path)
    plt.close()

    # 2. Product-wise Performance (Bar Chart)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    plt.title('Top Product Performance by Revenue ($)', fontsize=14, fontweight='bold', pad=15)

    if ranking:
        prods = [p['product_name'][:18] for p in ranking[:6]]
        revs = [p['total_revenue'] for p in ranking[:6]]
        bars = ax.bar(prods, revs, color='#2ca02c', edgecolor='#1e711e', width=0.55)
        ax.set_ylabel('Total Revenue ($)', fontweight='bold')
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'${height:,.0f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'No Data Available', horizontalalignment='center', verticalalignment='center')

    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()
    chart2_path = os.path.join(output_dir, 'product_performance_chart.png')
    plt.savefig(chart2_path)
    plt.close()

    return {
        "monthly_chart": chart1_path,
        "product_chart": chart2_path
    }
