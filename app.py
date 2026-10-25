"""
Sales Data Analysis System - Flask Web Application
RESTful API & Web Server
"""

import os
import json
import io
import csv
import unittest
from flask import Flask, request, jsonify, send_file
from database import init_db, save_sales_records, get_all_records, clear_all_sales
from analysis import validate_sales_csv, analyze_sales_records, generate_matplotlib_charts
import test_sales_analysis

app = Flask(__name__, static_folder=".", static_url_path="")

# Ensure database is initialized
init_db()

# Keep track of latest upload report in server memory
latest_import_report = {
    "has_report": False,
    "filename": None,
    "total_inspected": 0,
    "valid_count": 0,
    "invalid_count": 0,
    "duplicate_count": 0,
    "inserted": 0,
    "updated": 0,
    "skipped": 0,
    "applied_policy": "SKIP",
    "malformed_rows": []
}

# Auto-seed sample data if empty
existing = get_all_records()
if not existing:
    sample_csv_path = os.path.join(os.path.dirname(__file__), "sample_sales_data.csv")
    if os.path.exists(sample_csv_path):
        val = validate_sales_csv(sample_csv_path)
        if val["valid_rows"]:
            save_sales_records(val["valid_rows"], duplicate_policy="SKIP")

def is_database_sample_only():
    """Checks whether the database currently holds only the original demo sample records."""
    records = get_all_records()
    if not records:
        return False, 0
    # Sample records begin with S1001-S1025
    sample_ids = {f"S{i}" for i in range(1001, 1026)}
    curr_ids = {r['sale_id'] for r in records}
    is_sample = curr_ids.issubset(sample_ids) and len(records) <= 25
    return is_sample, len(records)

@app.route("/")
def index():
    return send_file("index.html")

@app.route("/api/summary", methods=["GET"])
def get_summary():
    records = get_all_records()
    analysis = analyze_sales_records(records)
    is_sample, count = is_database_sample_only()
    return jsonify({
        "status": "success",
        "data": analysis,
        "record_count": len(records),
        "is_sample_data": is_sample
    })

@app.route("/api/records", methods=["GET", "POST"])
def manage_records():
    if request.method == "GET":
        records = get_all_records()
        is_sample, _ = is_database_sample_only()
        return jsonify({
            "status": "success",
            "records": records,
            "is_sample_data": is_sample
        })

    # POST: Add individual record
    data = request.get_json() or {}
    required = ['sale_id', 'product_id', 'sale_date', 'quantity', 'unit_price', 'region']
    missing = [f for f in required if f not in data or str(data[f]).strip() == ""]
    if missing:
        return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        qty = int(data['quantity'])
        price = float(data['unit_price'])
        if qty <= 0:
            return jsonify({"status": "error", "message": "Quantity must be greater than 0"}), 400
        if price < 0:
            return jsonify({"status": "error", "message": "Unit price cannot be negative"}), 400
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid numeric format for quantity or price"}), 400

    record = [{
        "sale_id": str(data['sale_id']).strip(),
        "product_id": str(data['product_id']).strip(),
        "product_name": str(data.get('product_name') or f"Product {data['product_id']}").strip(),
        "category": str(data.get('category') or 'General').strip(),
        "sale_date": str(data['sale_date']).strip(),
        "quantity": qty,
        "unit_price": price,
        "region": str(data['region']).strip()
    }]
    policy = data.get("duplicate_policy", "SKIP")
    result = save_sales_records(record, duplicate_policy=policy)
    return jsonify({"status": "success", "result": result})

@app.route("/api/upload", methods=["POST"])
def upload_csv():
    global latest_import_report

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400

    duplicate_policy = request.form.get("duplicate_policy", "SKIP").upper()
    if duplicate_policy not in ["SKIP", "OVERWRITE", "APPEND"]:
        duplicate_policy = "SKIP"

    # Optional flag: clear sample data if currently in demo mode
    clear_sample = request.form.get("clear_sample", "false").lower() == "true"
    if clear_sample:
        is_sample, _ = is_database_sample_only()
        if is_sample:
            clear_all_sales()

    # Validate CSV content
    validation_res = validate_sales_csv(file)
    if validation_res["status"] == "error":
        return jsonify({
            "status": "error",
            "message": validation_res["message"],
            "filename": file.filename,
            "validation": {
                "total_inspected": validation_res.get("total_rows_inspected", 0),
                "valid_count": 0,
                "invalid_count": len(validation_res.get("malformed_rows", [])),
                "duplicate_count": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "applied_policy": duplicate_policy,
                "malformed_rows": validation_res.get("malformed_rows", [])
            }
        }), 400

    save_stats = {"inserted": 0, "updated": 0, "skipped": 0, "duplicates": 0}
    if validation_res["valid_rows"]:
        save_stats = save_sales_records(validation_res["valid_rows"], duplicate_policy=duplicate_policy)

    # Re-calculate analysis with updated database
    all_recs = get_all_records()
    analysis = analyze_sales_records(all_recs)

    # Optional: generate matplotlib charts
    try:
        generate_matplotlib_charts(all_recs)
    except Exception as e:
        print(f"Matplotlib chart notice: {e}")

    # Total duplicates is sum of in-file duplicates plus database collisions
    total_duplicates = validation_res["duplicate_count"] + save_stats.get("duplicates", 0)

    # Update latest server report
    latest_import_report = {
        "has_report": True,
        "filename": file.filename,
        "total_inspected": validation_res["total_rows_inspected"],
        "valid_count": len(validation_res["valid_rows"]),
        "invalid_count": len(validation_res["malformed_rows"]),
        "duplicate_count": total_duplicates,
        "inserted": save_stats.get("inserted", 0),
        "updated": save_stats.get("updated", 0),
        "skipped": save_stats.get("skipped", 0),
        "applied_policy": duplicate_policy,
        "malformed_rows": validation_res["malformed_rows"]
    }

    return jsonify({
        "status": "success",
        "filename": file.filename,
        "validation": latest_import_report,
        "summary": analysis["summary"]
    })

@app.route("/api/latest-report", methods=["GET"])
def get_latest_report():
    return jsonify({
        "status": "success",
        "report": latest_import_report
    })

@app.route("/api/reset-sample", methods=["POST"])
def reset_sample_data():
    """Resets database back to default verified sample sales records."""
    clear_all_sales()
    sample_csv_path = os.path.join(os.path.dirname(__file__), "sample_sales_data.csv")
    if os.path.exists(sample_csv_path):
        val = validate_sales_csv(sample_csv_path)
        if val["valid_rows"]:
            save_sales_records(val["valid_rows"], duplicate_policy="SKIP")
    return jsonify({"status": "success", "message": "Sample sales data restored successfully."})

@app.route("/api/clear-db", methods=["POST"])
def clear_db():
    """Clears all sales records for a blank slate import."""
    clear_all_sales()
    return jsonify({"status": "success", "message": "Database cleared. Ready for custom CSV import."})

@app.route("/api/run-tests", methods=["GET"])
def run_tests():
    """Runs the 14 automated verification tests for trainer assessment."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_sales_analysis)
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)

    output = stream.getvalue()
    return jsonify({
        "status": "success" if result.wasSuccessful() else "failed",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "details": output
    })

@app.route("/api/export-csv", methods=["GET"])
def export_csv():
    records = get_all_records()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['sale_id', 'product_id', 'product_name', 'category', 'sale_date', 'quantity', 'unit_price', 'total_amount', 'region'])
    for r in records:
        writer.writerow([
            r['sale_id'], r['product_id'], r['product_name'], r['category'],
            r['sale_date'], r['quantity'], r['unit_price'], r['total_amount'], r['region']
        ])

    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name='sales_data_export.csv')

if __name__ == "__main__":
    print("=====================================================")
    print("Sales Data Analysis System Web Server Running")
    print("Open http://127.0.0.1:5000 in your web browser")
    print("=====================================================")
    app.run(host="127.0.0.1", port=5000, debug=False)
