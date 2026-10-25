"""
Unit Test Suite for Sales Data Analysis System
Comprehensive verification of all 14 Project Requirements:
1.  Valid CSV uploads
2.  Missing required columns
3.  Invalid dates
4.  Missing sale IDs
5.  Invalid quantities (non-integer, zero, negative)
6.  Invalid and negative prices
7.  Missing required values (product_id, region, etc.)
8.  Duplicate IDs within one CSV
9.  Duplicate IDs already in the database
10. SKIP, OVERWRITE, and APPEND policies
11. Revenue calculations (total_amount = quantity * unit_price, sum, average)
12. Monthly aggregation and product rankings
13. CSV files containing both valid and invalid rows (partial import)
14. Empty CSV files and files containing only headers
"""

import unittest
import io
import os
import tempfile
from analysis import validate_sales_csv, analyze_sales_records
from database import init_db, save_sales_records, get_all_records, get_db_connection

class TestSalesAnalysisSystem(unittest.TestCase):

    def setUp(self):
        # Create an isolated temporary database for each test
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(db_file=self.temp_db_path)

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    # ------------------------------------------------------------------
    # 1. Valid CSV uploads
    # ------------------------------------------------------------------
    def test_01_valid_csv_upload(self):
        csv_data = """sale_id,product_id,product_name,category,sale_date,quantity,unit_price,region
S101,P1,Server Pro,Hardware,2026-01-10,5,1000.00,North America
S102,P2,Analytics,Software,2026-01-15,10,250.00,Europe
"""
        res = validate_sales_csv(io.StringIO(csv_data))
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["valid_rows"]), 2)
        self.assertEqual(len(res["malformed_rows"]), 0)
        self.assertEqual(res["total_rows_inspected"], 2)

    # ------------------------------------------------------------------
    # 2. Missing required columns
    # ------------------------------------------------------------------
    def test_02_missing_required_columns(self):
        # Missing 'region' and 'sale_date'
        csv_data = """sale_id,product_id,quantity,unit_price
S101,P1,5,1000.00
"""
        res = validate_sales_csv(io.StringIO(csv_data))
        self.assertEqual(res["status"], "error")
        self.assertIn("missing required column", res["message"].lower())
        self.assertEqual(len(res["valid_rows"]), 0)

    # ------------------------------------------------------------------
    # 3. Invalid dates
    # ------------------------------------------------------------------
    def test_03_invalid_dates(self):
        csv_data = """sale_id,product_id,sale_date,quantity,unit_price,region
S101,P1,NOT-A-DATE,5,100.00,Europe
S102,P1,2026-02-30,5,100.00,Europe
"""
        res = validate_sales_csv(io.StringIO(csv_data))
        self.assertEqual(len(res["valid_rows"]), 0)
        self.assertEqual(len(res["malformed_rows"]), 2)
        fields = [err["field"] for err in res["malformed_rows"]]
        self.assertTrue(all(f == "sale_date" for f in fields))

    # ------------------------------------------------------------------
    # 4. Missing sale IDs
    # ------------------------------------------------------------------
    def test_04_missing_sale_ids(self):
        csv_data = """sale_id,product_id,sale_date,quantity,unit_price,region
,P1,2026-01-10,5,100.00,North America
   ,P1,2026-01-11,5,100.00,North America
"""
        res = validate_sales_csv(io.StringIO(csv_data))
        self.assertEqual(len(res["valid_rows"]), 0)
        self.assertEqual(len(res["malformed_rows"]), 2)
        self.assertEqual(res["malformed_rows"][0]["field"], "sale_id")

    # ------------------------------------------------------------------
    # 5. Invalid quantities (non-integer, zero, negative)
    # ------------------------------------------------------------------
    def test_05_invalid_quantities(self):
        csv_data = """sale_id,product_id,sale_date,quantity,unit_price,region
S1,P1,2026-01-10,0,100.00,North America
S2,P1,2026-01-11,-5,100.00,North America
S3,P1,2026-01-12,abc,100.00,North America
S4,P1,2026-01-13,4.5,100.00,North America
"""
        res = validate_sales_csv(io.StringIO(csv_data))
        self.assertEqual(len(res["valid_rows"]), 0)
        self.assertEqual(len(res["malformed_rows"]), 4)
        for err in res["malformed_rows"]:
            self.assertEqual(err["field"], "quantity")

    # ------------------------------------------------------------------
    # 6. Invalid and negative prices
    # ------------------------------------------------------------------
    def test_06_invalid_and_negative_prices(self):
        csv_data = """sale_id,product_id,sale_date,quantity,unit_price,region
S1,P1,2026-01-10,5,-10.00,North America
S2,P1,2026-01-11,5,NOT_PRICE,North America
"""
        res = validate_sales_csv(io.StringIO(csv_data))
        self.assertEqual(len(res["valid_rows"]), 0)
        self.assertEqual(len(res["malformed_rows"]), 2)
        for err in res["malformed_rows"]:
            self.assertEqual(err["field"], "unit_price")

    # ------------------------------------------------------------------
    # 7. Missing required values (product_id, region)
    # ------------------------------------------------------------------
    def test_07_missing_required_values(self):
        csv_data = """sale_id,product_id,sale_date,quantity,unit_price,region
S1,,2026-01-10,5,100.00,North America
S2,P1,2026-01-11,5,100.00,
"""
        res = validate_sales_csv(io.StringIO(csv_data))
        self.assertEqual(len(res["valid_rows"]), 0)
        self.assertEqual(len(res["malformed_rows"]), 2)
        err_fields = [err["field"] for err in res["malformed_rows"]]
        self.assertIn("product_id", err_fields)
        self.assertIn("region", err_fields)

    # ------------------------------------------------------------------
    # 8. Duplicate IDs within one CSV
    # ------------------------------------------------------------------
    def test_08_duplicate_ids_within_one_csv(self):
        csv_data = """sale_id,product_id,sale_date,quantity,unit_price,region
S100,P1,2026-01-10,5,100.00,North America
S100,P1,2026-01-12,10,100.00,North America
"""
        res = validate_sales_csv(io.StringIO(csv_data))
        self.assertEqual(res["duplicate_count"], 1)
        self.assertIn("S100", res["duplicate_ids"])
        # The duplicate appearance is reported in malformed_rows
        dup_errors = [e for e in res["malformed_rows"] if e.get("is_duplicate")]
        self.assertEqual(len(dup_errors), 1)
        self.assertEqual(dup_errors[0]["field"], "sale_id")

    # ------------------------------------------------------------------
    # 9. Duplicate IDs already in the database
    # ------------------------------------------------------------------
    def test_09_duplicate_ids_already_in_database(self):
        # Insert initial record
        record1 = [{
            "sale_id": "EXISTING_01",
            "product_id": "P101",
            "product_name": "Server",
            "category": "Hardware",
            "sale_date": "2026-01-01",
            "quantity": 2,
            "unit_price": 500.00,
            "region": "Europe"
        }]
        save_sales_records(record1, duplicate_policy="SKIP", db_file=self.temp_db_path)

        # Attempt to insert same sale_id
        record2 = [{
            "sale_id": "EXISTING_01",
            "product_id": "P101",
            "product_name": "Server",
            "category": "Hardware",
            "sale_date": "2026-01-01",
            "quantity": 10,
            "unit_price": 500.00,
            "region": "Europe"
        }]
        stats = save_sales_records(record2, duplicate_policy="SKIP", db_file=self.temp_db_path)
        self.assertEqual(stats["duplicates"], 1)
        self.assertEqual(stats["skipped"], 1)
        self.assertEqual(stats["inserted"], 0)

    # ------------------------------------------------------------------
    # 10. SKIP, OVERWRITE, and APPEND policies
    # ------------------------------------------------------------------
    def test_10_duplicate_policies(self):
        # 1. Base record
        base = [{
            "sale_id": "POL_TEST",
            "product_id": "P101",
            "product_name": "Item",
            "category": "Hardware",
            "sale_date": "2026-01-01",
            "quantity": 1,
            "unit_price": 100.00,
            "region": "North America"
        }]
        save_sales_records(base, duplicate_policy="SKIP", db_file=self.temp_db_path)

        # 2. Test SKIP: Quantity should remain 1
        incoming_skip = [{
            "sale_id": "POL_TEST",
            "product_id": "P101",
            "product_name": "Item",
            "category": "Hardware",
            "sale_date": "2026-01-01",
            "quantity": 99,
            "unit_price": 100.00,
            "region": "North America"
        }]
        res_skip = save_sales_records(incoming_skip, duplicate_policy="SKIP", db_file=self.temp_db_path)
        self.assertEqual(res_skip["skipped"], 1)

        conn = get_db_connection(self.temp_db_path)
        row = conn.execute("SELECT quantity FROM sales WHERE sale_id='POL_TEST'").fetchone()
        self.assertEqual(row["quantity"], 1)

        # 3. Test OVERWRITE: Quantity should update to 50
        incoming_overwrite = [{
            "sale_id": "POL_TEST",
            "product_id": "P101",
            "product_name": "Item",
            "category": "Hardware",
            "sale_date": "2026-01-01",
            "quantity": 50,
            "unit_price": 100.00,
            "region": "North America"
        }]
        res_ovw = save_sales_records(incoming_overwrite, duplicate_policy="OVERWRITE", db_file=self.temp_db_path)
        self.assertEqual(res_ovw["updated"], 1)

        row = conn.execute("SELECT quantity, total_amount FROM sales WHERE sale_id='POL_TEST'").fetchone()
        self.assertEqual(row["quantity"], 50)
        self.assertEqual(row["total_amount"], 5000.00)

        # 4. Test APPEND: Inserts with unique suffixed ID
        incoming_append = [{
            "sale_id": "POL_TEST",
            "product_id": "P101",
            "product_name": "Item",
            "category": "Hardware",
            "sale_date": "2026-01-01",
            "quantity": 5,
            "unit_price": 100.00,
            "region": "North America"
        }]
        res_app = save_sales_records(incoming_append, duplicate_policy="APPEND", db_file=self.temp_db_path)
        self.assertEqual(res_app["inserted"], 1)

        recs = conn.execute("SELECT sale_id FROM sales WHERE sale_id LIKE 'POL_TEST%'").fetchall()
        self.assertEqual(len(recs), 2)
        sale_ids = [r["sale_id"] for r in recs]
        self.assertIn("POL_TEST", sale_ids)
        self.assertIn("POL_TEST_dup1", sale_ids)
        conn.close()

    # ------------------------------------------------------------------
    # 11. Revenue calculations
    # ------------------------------------------------------------------
    def test_11_revenue_calculations(self):
        records = [
            {"sale_id": "S1", "product_id": "P1", "sale_date": "2026-01-10", "quantity": 4, "unit_price": 250.00, "region": "North America"},
            {"sale_id": "S2", "product_id": "P2", "sale_date": "2026-01-15", "quantity": 10, "unit_price": 150.00, "region": "Europe"}
        ]
        # S1: 4 * 250 = 1000.00
        # S2: 10 * 150 = 1500.00
        # Total = 2500.00, Units = 14, Count = 2, Avg = 1250.00
        res = analyze_sales_records(records)
        s = res["summary"]
        self.assertEqual(s["total_revenue"], 2500.00)
        self.assertEqual(s["total_units"], 14)
        self.assertEqual(s["total_transactions"], 2)
        self.assertEqual(s["avg_order_value"], 1250.00)

    # ------------------------------------------------------------------
    # 12. Monthly aggregation and product rankings
    # ------------------------------------------------------------------
    def test_12_monthly_aggregation_and_product_rankings(self):
        records = [
            {"sale_id": "S1", "product_id": "P1", "product_name": "Product A", "category": "Hardware", "sale_date": "2026-01-10", "quantity": 5, "unit_price": 100.00, "region": "North America"},
            {"sale_id": "S2", "product_id": "P2", "product_name": "Product B", "category": "Software", "sale_date": "2026-02-15", "quantity": 10, "unit_price": 200.00, "region": "Europe"}
        ]
        res = analyze_sales_records(records)
        monthly = res["monthly_trends"]
        self.assertEqual(len(monthly), 2)
        self.assertEqual(monthly[0]["month"], "2026-01")
        self.assertEqual(monthly[0]["revenue"], 500.00)
        self.assertEqual(monthly[1]["month"], "2026-02")
        self.assertEqual(monthly[1]["revenue"], 2000.00)

        # MoM growth: (2000 - 500) / 500 * 100 = 300.0%
        self.assertEqual(res["summary"]["monthly_growth_rate"], 300.0)

        # Product ranking: Product B has 2000.00, rank 1; Product A has 500.00, rank 2
        ranks = res["product_ranking"]
        self.assertEqual(ranks[0]["product_id"], "P2")
        self.assertEqual(ranks[0]["total_revenue"], 2000.00)
        self.assertEqual(ranks[1]["product_id"], "P1")
        self.assertEqual(ranks[1]["total_revenue"], 500.00)

    # ------------------------------------------------------------------
    # 13. CSV files containing both valid and invalid rows (partial import)
    # ------------------------------------------------------------------
    def test_13_mixed_valid_and_invalid_rows(self):
        csv_data = """sale_id,product_id,product_name,category,sale_date,quantity,unit_price,region
S1,P1,Valid Item 1,Hardware,2026-01-01,5,100.00,North America
S2,,Invalid Item (Missing ID),Hardware,2026-01-02,5,100.00,North America
S3,P2,Invalid Item (Negative Qty),Hardware,2026-01-03,-10,100.00,North America
S4,P3,Valid Item 2,Software,2026-01-04,2,300.00,Europe
"""
        res = validate_sales_csv(io.StringIO(csv_data))
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["valid_rows"]), 2)
        self.assertEqual(len(res["malformed_rows"]), 2)
        self.assertEqual(res["total_rows_inspected"], 4)

        # Partial import verification
        stats = save_sales_records(res["valid_rows"], duplicate_policy="SKIP", db_file=self.temp_db_path)
        self.assertEqual(stats["inserted"], 2)
        saved = get_all_records(db_file=self.temp_db_path)
        self.assertEqual(len(saved), 2)
        saved_ids = [r["sale_id"] for r in saved]
        self.assertIn("S1", saved_ids)
        self.assertIn("S4", saved_ids)

    # ------------------------------------------------------------------
    # 14. Empty CSV files and files containing only headers
    # ------------------------------------------------------------------
    def test_14_empty_csv_and_headers_only(self):
        # A: Completely empty file
        empty_res = validate_sales_csv(io.StringIO(""))
        self.assertEqual(empty_res["status"], "error")
        self.assertEqual(empty_res["total_rows_inspected"], 0)

        # B: File with only headers
        headers_only = "sale_id,product_id,product_name,category,sale_date,quantity,unit_price,region\n"
        header_res = validate_sales_csv(io.StringIO(headers_only))
        self.assertEqual(header_res["status"], "success")
        self.assertEqual(header_res["total_rows_inspected"], 0)
        self.assertEqual(len(header_res["valid_rows"]), 0)
        self.assertEqual(len(header_res["malformed_rows"]), 0)

if __name__ == "__main__":
    unittest.main()
