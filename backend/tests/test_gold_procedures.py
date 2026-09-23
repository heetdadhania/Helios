import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCEDURES_DIR = os.path.join(REPO_ROOT, "database", "gold", "procedures")


class TestGoldStoredProcedures(unittest.TestCase):
    """Test suite validating Databricks SQL Stored Procedures for Gold layer transformations."""

    EXPECTED_FILES = [
        "01_sp_load_dim_date.sql",
        "02_sp_load_dim_product.sql",
        "03_sp_load_dim_customer.sql",
        "04_sp_load_dim_shipping_mode.sql",
        "05_sp_load_dim_delivery_status.sql",
        "06_sp_load_fact_orders.sql",
        "07_sp_load_fact_shipments.sql",
        "08_sp_refresh_daily_summary.sql",
        "09_sp_run_gold_pipeline.sql",
    ]

    def test_all_expected_procedures_exist(self):
        self.assertTrue(os.path.isdir(PROCEDURES_DIR), f"Directory {PROCEDURES_DIR} does not exist")
        actual_files = sorted(os.listdir(PROCEDURES_DIR))
        for exp in self.EXPECTED_FILES:
            self.assertIn(exp, actual_files, f"Missing procedure file: {exp}")

    def _read_proc(self, filename: str) -> str:
        filepath = os.path.join(PROCEDURES_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def test_procedure_signatures_and_syntax(self):
        for fname in self.EXPECTED_FILES:
            content = self._read_proc(fname)
            self.assertIn("CREATE OR REPLACE PROCEDURE", content, f"Missing procedure definition in {fname}")
            self.assertIn("LANGUAGE SQL", content, f"Missing LANGUAGE SQL in {fname}")
            self.assertIn("AS BEGIN", content, f"Missing AS BEGIN in {fname}")
            self.assertTrue(content.strip().endswith("END;"), f"Procedure {fname} does not terminate with END;")
            # All procedures accept tenant_id_param and batch_id_param
            self.assertIn("tenant_id_param BIGINT", content, f"Missing tenant_id_param in {fname}")
            self.assertIn("batch_id_param STRING", content, f"Missing batch_id_param in {fname}")

    def test_dimension_procedures_use_merge_into(self):
        dim_files = [
            "01_sp_load_dim_date.sql",
            "02_sp_load_dim_product.sql",
            "03_sp_load_dim_customer.sql",
            "04_sp_load_dim_shipping_mode.sql",
            "05_sp_load_dim_delivery_status.sql",
            "08_sp_refresh_daily_summary.sql",
        ]
        for fname in dim_files:
            content = self._read_proc(fname)
            self.assertIn("MERGE INTO", content, f"Expected MERGE INTO construct in {fname}")
            self.assertIn("WHEN NOT MATCHED THEN", content, f"Expected WHEN NOT MATCHED in {fname}")

    def test_tenant_scoping_in_tenant_dimensions(self):
        tenant_dims = [
            "02_sp_load_dim_product.sql",
            "03_sp_load_dim_customer.sql",
            "06_sp_load_fact_orders.sql",
            "07_sp_load_fact_shipments.sql",
            "08_sp_refresh_daily_summary.sql",
        ]
        for fname in tenant_dims:
            content = self._read_proc(fname)
            self.assertIn("tenant_id = tenant_id_param", content, f"Expected tenant scoping in {fname}")

    def test_fact_loading_procedures(self):
        orders_content = self._read_proc("06_sp_load_fact_orders.sql")
        self.assertIn("INSERT INTO helios.gold.fact_orders", orders_content)
        self.assertIn("helios.silver.orders_clean", orders_content)
        self.assertIn("helios.gold.dim_product", orders_content)
        self.assertIn("helios.gold.dim_customer", orders_content)
        self.assertIn("helios.gold.dim_date", orders_content)

        ship_content = self._read_proc("07_sp_load_fact_shipments.sql")
        self.assertIn("INSERT INTO helios.gold.fact_shipments", ship_content)
        self.assertIn("helios.silver.shipping_clean", ship_content)
        self.assertIn("helios.gold.dim_shipping_mode", ship_content)
        self.assertIn("helios.gold.dim_delivery_status", ship_content)

    def test_daily_summary_procedure(self):
        summary_content = self._read_proc("08_sp_refresh_daily_summary.sql")
        self.assertIn("MERGE INTO helios.gold.fact_orders_daily_summary", summary_content)
        self.assertIn("count(DISTINCT fo.source_order_id) AS total_orders", summary_content)
        self.assertIn("round(sum(coalesce(fo.total, 0.0000)), 4) AS total_revenue", summary_content)

    def test_master_orchestration_procedure(self):
        master_content = self._read_proc("09_sp_run_gold_pipeline.sql")
        # Check that all 8 sub-procedures are called in order
        calls = [
            "CALL helios.gold.sp_load_dim_date",
            "CALL helios.gold.sp_load_dim_product",
            "CALL helios.gold.sp_load_dim_customer",
            "CALL helios.gold.sp_load_dim_shipping_mode",
            "CALL helios.gold.sp_load_dim_delivery_status",
            "CALL helios.gold.sp_load_fact_orders",
            "CALL helios.gold.sp_load_fact_shipments",
            "CALL helios.gold.sp_refresh_daily_summary",
        ]
        last_pos = -1
        for call_stmt in calls:
            pos = master_content.find(call_stmt)
            self.assertNotEqual(pos, -1, f"Missing invocation: {call_stmt}")
            self.assertGreater(pos, last_pos, f"Invocation {call_stmt} is out of order")
            last_pos = pos

        # Check exception handling
        self.assertIn("DECLARE EXIT HANDLER FOR SQLEXCEPTION", master_content)
        self.assertIn("stage = 'gold'", master_content)
        self.assertIn("status = 'failed'", master_content)

        # Check success handling
        self.assertIn("stage = 'gold_transform'", master_content)
        self.assertIn("status = 'success'", master_content)
        self.assertIn("INSERT INTO helios.meta.etl_audit_log", master_content)


if __name__ == "__main__":
    unittest.main()
